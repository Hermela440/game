import requests
import json
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Optional, Tuple
from models.transaction import Transaction, TransactionType, TransactionStatus, PaymentMethod
from models.user import User
from database import db
from encryption_manager import EncryptionManager
from signature_manager import SignatureManager
from transaction_validator import TransactionValidator

class WalletManager:
    def __init__(self, api_key: str, api_secret: str, webhook_secret: str, encryption_key: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.webhook_secret = webhook_secret
        self.base_url = "https://api.capawallet.com/v1"
        self.encryption_manager = EncryptionManager(encryption_key)
        self.signature_manager = SignatureManager(api_secret)
        self.transaction_validator = TransactionValidator()
        
    def _generate_reference(self, user_id: int) -> str:
        """Generate a unique transaction reference."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        return f"CAPA_{user_id}_{timestamp}"
    
    def _get_headers(self, data: Dict) -> Dict[str, str]:
        """Get headers for Capa Wallet API requests with signature."""
        headers = self.signature_manager.get_signed_headers(data)
        headers['Authorization'] = f"Bearer {self.api_key}"
        return headers
    
    def get_wallet_balance(self, user: User) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get user's Capa Wallet balance.
        
        Args:
            user: User object
            
        Returns:
            Tuple of (success, message, balance_data)
        """
        try:
            # Prepare balance request data
            balance_data = {
                "user_id": user.id
            }
            
            # Make API request to Capa Wallet with signed headers
            response = requests.get(
                f"{self.base_url}/wallet/balance",
                headers=self._get_headers(balance_data),
                params=balance_data
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "success":
                    return True, "Balance retrieved successfully", response_data["data"]
                else:
                    return False, "Failed to retrieve balance", None
            else:
                return False, f"API request failed: {response.text}", None
                
        except Exception as e:
            return False, f"Error retrieving balance: {str(e)}", None
    
    def withdraw_funds(self, user: User, amount: float, currency: str = "USD", wallet_details: Optional[Dict] = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Withdraw funds from user's Capa Wallet.
        
        Args:
            user: User object
            amount: Withdrawal amount
            currency: Currency code (default: USD)
            wallet_details: Optional wallet details to encrypt
            
        Returns:
            Tuple of (success, message, withdrawal_data)
        """
        try:
            # Validate withdrawal
            is_valid, message = self.transaction_validator.validate_withdrawal(user, amount)
            if not is_valid:
                return False, message, None
            
            # Create transaction record
            transaction = Transaction(
                user_id=user.id,
                type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.PENDING,
                amount=amount,
                balance_before=user.balance,
                payment_method=PaymentMethod.CAPA_WALLET,
                transaction_id=self._generate_reference(user.id),
                description=f"Withdrawal to Capa Wallet - {currency} {amount}"
            )
            
            # Encrypt wallet details if provided
            if wallet_details:
                transaction.payment_details = self.encryption_manager.encrypt_payment_details(wallet_details)
            
            db.session.add(transaction)
            db.session.commit()
            
            # Prepare withdrawal data
            withdrawal_data = {
                "amount": str(amount),
                "currency": currency,
                "user_id": user.id,
                "reference": transaction.transaction_id,
                "callback_url": f"https://your-domain.com/api/wallet/webhook"
            }
            
            # Make API request to Capa Wallet with signed headers
            response = requests.post(
                f"{self.base_url}/wallet/withdraw",
                headers=self._get_headers(withdrawal_data),
                json=withdrawal_data
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "success":
                    # Update transaction with withdrawal details
                    transaction.payment_details = self.encryption_manager.encrypt_payment_details(response_data["data"])
                    db.session.commit()
                    return True, "Withdrawal initiated successfully", response_data["data"]
                else:
                    transaction.status = TransactionStatus.FAILED
                    db.session.commit()
                    return False, "Withdrawal initiation failed", None
            else:
                transaction.status = TransactionStatus.FAILED
                db.session.commit()
                return False, f"API request failed: {response.text}", None
                
        except Exception as e:
            return False, f"Error initiating withdrawal: {str(e)}", None
    
    def handle_webhook(self, payload: Dict, signature: str) -> Tuple[bool, str]:
        """
        Handle Capa Wallet webhook notifications.
        
        Args:
            payload: Webhook payload
            signature: Webhook signature for verification
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify webhook signature
            if not self._verify_webhook_signature(payload, signature):
                return False, "Invalid webhook signature"
            
            # Extract transaction details
            transaction_id = payload.get("reference")
            status = payload.get("status")
            
            if not transaction_id or not status:
                return False, "Invalid webhook payload"
            
            # Get transaction from database
            transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
            if not transaction:
                return False, "Transaction not found"
            
            # Update transaction status
            if status == "completed":
                transaction.status = TransactionStatus.COMPLETED
                transaction.payment_details = self.encryption_manager.encrypt_payment_details(payload)
                
                # Update user balance
                user = User.query.get(transaction.user_id)
                if user:
                    user.balance -= transaction.amount
                    transaction.balance_after = user.balance
                    db.session.commit()
                    
                return True, "Withdrawal processed successfully"
            elif status == "failed":
                transaction.status = TransactionStatus.FAILED
                db.session.commit()
                return False, "Withdrawal failed"
            else:
                return False, f"Unknown status: {status}"
                
        except Exception as e:
            return False, f"Error processing webhook: {str(e)}"
    
    def _verify_webhook_signature(self, payload: Dict, signature: str) -> bool:
        """Verify webhook signature."""
        try:
            # Convert payload to string
            payload_str = json.dumps(payload, sort_keys=True)
            
            # Calculate HMAC
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception:
            return False
    
    def get_transaction_limits(self, user: User) -> Dict[str, float]:
        """
        Get transaction limits for a user.
        
        Args:
            user: User object
            
        Returns:
            Dictionary of transaction limits
        """
        return self.transaction_validator.get_remaining_limits(user) 