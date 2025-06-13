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

class PaymentManager:
    def __init__(self, api_key: str, api_secret: str, webhook_secret: str, encryption_key: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.webhook_secret = webhook_secret
        self.base_url = "https://api.chapa.co/v1"
        self.encryption_manager = EncryptionManager(encryption_key)
        self.signature_manager = SignatureManager(api_secret)
        self.transaction_validator = TransactionValidator()
        
    def _generate_reference(self, user_id: int) -> str:
        """Generate a unique transaction reference."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        return f"CHAPA-{user_id}-{timestamp}"
    
    def _get_headers(self, data: Dict) -> Dict:
        """
        Get headers for API request with signature.
        
        Args:
            data: Request data to sign
            
        Returns:
            Dictionary of headers
        """
        return self.signature_manager.get_signed_headers(data)
    
    def initiate_payment(self, user: User, amount: float, currency: str = "USD", payment_details: Optional[Dict] = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Initiate a payment transaction.
        
        Args:
            user: User object
            amount: Payment amount
            currency: Currency code (default: USD)
            payment_details: Optional payment details to encrypt
            
        Returns:
            Tuple of (success, message, payment_data)
        """
        try:
            # Validate deposit
            is_valid, message = self.transaction_validator.validate_deposit(user, amount)
            if not is_valid:
                return False, message, None
            
            # Create transaction record
            transaction = Transaction(
                user_id=user.id,
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.PENDING,
                amount=amount,
                balance_before=user.balance,
                payment_method=PaymentMethod.CHAPA,
                transaction_id=self._generate_reference(user.id),
                description=f"Deposit via Chapa - {currency} {amount}"
            )
            
            # Encrypt payment details if provided
            if payment_details:
                transaction.payment_details = self.encryption_manager.encrypt_payment_details(payment_details)
            
            db.session.add(transaction)
            db.session.commit()
            
            # Prepare payment data
            payment_data = {
                "amount": str(amount),
                "currency": currency,
                "email": user.email,
                "first_name": user.username,
                "last_name": "",
                "tx_ref": transaction.transaction_id,
                "callback_url": f"https://your-domain.com/api/payment/webhook",
                "return_url": "https://your-domain.com/payment/success"
            }
            
            # Make API request to Chapa with signed headers
            response = requests.post(
                f"{self.base_url}/transaction/initialize",
                headers=self._get_headers(payment_data),
                json=payment_data
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "success":
                    # Update transaction with payment details
                    transaction.payment_details = self.encryption_manager.encrypt_payment_details(response_data["data"])
                    db.session.commit()
                    return True, "Payment initiated successfully", response_data["data"]
                else:
                    transaction.status = TransactionStatus.FAILED
                    db.session.commit()
                    return False, "Payment initiation failed", None
            else:
                transaction.status = TransactionStatus.FAILED
                db.session.commit()
                return False, f"API request failed: {response.text}", None
                
        except Exception as e:
            return False, f"Error initiating payment: {str(e)}", None
    
    def verify_payment(self, transaction_id: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Verify a payment transaction.
        
        Args:
            transaction_id: Transaction reference ID
            
        Returns:
            Tuple of (success, message, verification_data)
        """
        try:
            # Get transaction
            transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
            if not transaction:
                return False, "Transaction not found", None
                
            # Prepare verification data
            verification_data = {
                "tx_ref": transaction_id
            }
            
            # Make API request to Chapa with signed headers
            response = requests.get(
                f"{self.base_url}/transaction/verify/{transaction_id}",
                headers=self._get_headers(verification_data)
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "success":
                    # Update transaction with verification details
                    transaction.payment_details = self.encryption_manager.encrypt_payment_details(response_data["data"])
                    db.session.commit()
                    return True, "Payment verified successfully", response_data["data"]
                else:
                    return False, "Payment verification failed", None
            else:
                return False, f"API request failed: {response.text}", None
                
        except Exception as e:
            return False, f"Error verifying payment: {str(e)}", None
    
    def handle_webhook(self, payload: Dict) -> Tuple[bool, str]:
        """
        Handle payment webhook notification.
        
        Args:
            payload: Webhook payload
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify webhook signature
            if not self.signature_manager.verify_request(payload):
                return False, "Invalid webhook signature"
                
            # Get transaction
            transaction_id = payload.get("tx_ref")
            transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
            if not transaction:
                return False, "Transaction not found"
                
            # Update transaction status
            if payload.get("status") == "success":
                transaction.status = TransactionStatus.COMPLETED
                
                # Update user balance
                user = User.query.get(transaction.user_id)
                if user:
                    user.balance += transaction.amount
                    
                # Update transaction details
                transaction.payment_details = self.encryption_manager.encrypt_payment_details(payload)
                
            else:
                transaction.status = TransactionStatus.FAILED
                
            db.session.commit()
            return True, "Webhook processed successfully"
            
        except Exception as e:
            return False, f"Error processing webhook: {str(e)}"
    
    def get_transaction_limits(self, user: User) -> Dict[str, float]:
        """
        Get transaction limits for a user.
        
        Args:
            user: User object
            
        Returns:
            Dictionary of transaction limits
        """
        return self.transaction_validator.get_remaining_limits(user) 