# Bot Command Guide

## Overview

The bot provides various commands for managing games, wallets, and user interactions. All commands are prefixed with `/` and can be used in-game or in designated bot channels.

## Basic Commands

### Help
```
/help [command]
```
Shows available commands or detailed help for a specific command.
- Example: `/help deposit`
- Permission: Everyone

### Balance
```
/balance
```
Shows your current wallet balance.
- Example: `/balance`
- Response: `Your balance: $1,000.00`
- Permission: Everyone

### Profile
```
/profile [@user]
```
Shows your profile or another user's profile if specified.
- Example: `/profile @johndoe`
- Permission: Everyone

## Wallet Commands

### Deposit
```
/deposit <amount> [currency]
```
Initiates a deposit to your wallet.
- Example: `/deposit 100 USD`
- Response: `Deposit initiated. Please complete the payment at: [payment_link]`
- Permission: Everyone

### Withdraw
```
/withdraw <amount> [currency] <wallet_address>
```
Initiates a withdrawal from your wallet.
- Example: `/withdraw 50 USD 0x1234567890abcdef`
- Response: `Withdrawal initiated. Estimated completion: 10 minutes`
- Permission: Everyone

### Transfer
```
/transfer <@user> <amount> [currency]
```
Transfers funds to another user.
- Example: `/transfer @johndoe 25 USD`
- Response: `Transfer successful. New balance: $975.00`
- Permission: Everyone

## Game Commands

### Create Game
```
/create <game_type> <min_bet> <max_bet> [options]
```
Creates a new game room.
- Example: `/create poker 10 1000 --max-players 6 --time-limit 30`
- Response: `Game room created! Room code: ABC123`
- Permission: Everyone

### Join Game
```
/join <room_code> <bet_amount>
```
Joins an existing game room.
- Example: `/join ABC123 50`
- Response: `Joined game room. Position: 3`
- Permission: Everyone

### Leave Game
```
/leave
```
Leaves the current game room.
- Example: `/leave`
- Response: `Left game room. Funds returned to wallet.`
- Permission: Everyone

### Game Status
```
/status
```
Shows current game status.
- Example: `/status`
- Response: `Game in progress. Round 3. Pot: $150.00`
- Permission: Everyone

## Admin Commands

### Ban User
```
/ban <@user> <duration> [reason]
```
Bans a user from the platform.
- Example: `/ban @johndoe 24h "Violation of rules"`
- Permission: Admin

### Unban User
```
/unban <@user>
```
Removes a user's ban.
- Example: `/unban @johndoe`
- Permission: Admin

### Set Balance
```
/setbalance <@user> <amount> [currency]
```
Sets a user's balance (admin only).
- Example: `/setbalance @johndoe 1000 USD`
- Permission: Admin

### Maintenance
```
/maintenance <on|off> [reason]
```
Toggles maintenance mode.
- Example: `/maintenance on "Scheduled update"`
- Permission: Admin

## Moderation Commands

### Mute User
```
/mute <@user> <duration> [reason]
```
Mutes a user in the chat.
- Example: `/mute @johndoe 1h "Spam"`
- Permission: Moderator

### Unmute User
```
/unmute <@user>
```
Removes a user's mute.
- Example: `/unmute @johndoe`
- Permission: Moderator

### Clear Chat
```
/clear [amount]
```
Clears specified number of messages.
- Example: `/clear 50`
- Permission: Moderator

## Support Commands

### Report
```
/report <@user> <reason>
```
Reports a user for review.
- Example: `/report @johndoe "Suspicious behavior"`
- Permission: Everyone

### Support
```
/support <message>
```
Opens a support ticket.
- Example: `/support "Can't withdraw funds"`
- Permission: Everyone

### Feedback
```
/feedback <message>
```
Submits feedback to the development team.
- Example: `/feedback "Add more game types"`
- Permission: Everyone

## Game-Specific Commands

### Poker Commands
```
/fold
/call
/raise <amount>
/check
```
Poker game actions.
- Permission: Game participants

### Blackjack Commands
```
/hit
/stand
/double
/split
```
Blackjack game actions.
- Permission: Game participants

### Roulette Commands
```
/bet <number|color> <amount>
/spin
```
Roulette game actions.
- Permission: Game participants

## Command Options

### Global Options
- `--help`: Show help for the command
- `--verbose`: Show detailed information
- `--silent`: Suppress confirmation messages

### Game Options
- `--max-players`: Set maximum players
- `--time-limit`: Set time limit per round
- `--auto-start`: Enable/disable auto-start
- `--private`: Make game room private

### Moderation Options
- `--reason`: Specify reason for action
- `--duration`: Set duration for temporary actions
- `--notify`: Send notification to user

## Command Permissions

### User Levels
1. **Everyone**: Basic commands
2. **Verified**: Additional wallet features
3. **Moderator**: Moderation commands
4. **Admin**: Administrative commands

### Permission Requirements
- Wallet commands require email verification
- Game commands require sufficient balance
- Moderation commands require appropriate role
- Admin commands require admin privileges

## Error Messages

### Common Errors
- `Insufficient balance`
- `Invalid command syntax`
- `Permission denied`
- `User not found`
- `Game room full`
- `Invalid bet amount`

### Error Handling
- Commands will provide clear error messages
- Suggestions for correct usage
- Links to relevant documentation
- Support contact information

## Best Practices

### Command Usage
1. Use correct syntax and parameters
2. Check permissions before using commands
3. Verify amounts before transactions
4. Use appropriate channels for commands
5. Follow community guidelines

### Security
1. Never share your password
2. Use 2FA when available
3. Report suspicious activity
4. Keep your session secure
5. Log out when finished

## Support

For additional help:
- Use `/help` for command information
- Contact support with `/support`
- Check the documentation
- Join the community Discord
- Follow official social media 