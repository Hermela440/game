class GameClient {
    constructor(token) {
        this.token = token;
        this.socket = null;
        this.currentRoom = null;
        this.currentGame = null;
        this.handlers = {};
        this.gameState = null;
        this.initializeSocket();
    }

    initializeSocket() {
        // Connect to WebSocket server
        this.socket = io(window.location.origin, {
            query: { token: this.token }
        });

        // Set up event handlers
        this.socket.on('connect', () => this.handleConnect());
        this.socket.on('disconnect', () => this.handleDisconnect());
        this.socket.on('error', (data) => this.handleError(data));
        
        // Room events
        this.socket.on('room_created', (data) => this.handleRoomCreated(data));
        this.socket.on('room_joined', (data) => this.handleRoomJoined(data));
        this.socket.on('room_left', (data) => this.handleRoomLeft(data));
        this.socket.on('room_ready', (data) => this.handleRoomReady(data));
        this.socket.on('room_closed', (data) => this.handleRoomClosed(data));
        this.socket.on('available_rooms', (data) => this.handleAvailableRooms(data));
        this.socket.on('room_status', (data) => this.handleRoomStatus(data));
        
        // Game events
        this.socket.on('game_started', (data) => this.handleGameStarted(data));
        this.socket.on('round_started', (data) => this.handleRoundStarted(data));
        this.socket.on('player_turn', (data) => this.handlePlayerTurn(data));
        this.socket.on('game_state_update', (data) => this.handleGameStateUpdate(data));
        this.socket.on('game_over', (data) => this.handleGameOver(data));
        this.socket.on('game_state', (data) => this.handleGameState(data));
    }

    // Event handlers
    handleConnect() {
        console.log('Connected to server');
        this.trigger('connected');
    }

    handleDisconnect() {
        console.log('Disconnected from server');
        this.trigger('disconnected');
    }

    handleError(data) {
        console.error('Error:', data.message);
        this.trigger('error', data);
    }

    handleRoomCreated(data) {
        console.log('Room created:', data);
        this.currentRoom = data.room_id;
        this.trigger('room_created', data);
    }

    handleRoomJoined(data) {
        console.log('Joined room:', data);
        this.currentRoom = data.room_id;
        this.trigger('room_joined', data);
    }

    handleRoomLeft(data) {
        console.log('Left room:', data);
        if (this.currentRoom === data.room_id) {
            this.currentRoom = null;
        }
        this.trigger('room_left', data);
    }

    handleRoomReady(data) {
        console.log('Room ready:', data);
        this.trigger('room_ready', data);
    }

    handleRoomClosed(data) {
        console.log('Room closed:', data);
        if (this.currentRoom === data.room_id) {
            this.currentRoom = null;
        }
        this.trigger('room_closed', data);
    }

    handleAvailableRooms(data) {
        console.log('Available rooms:', data);
        this.trigger('available_rooms', data);
    }

    handleRoomStatus(data) {
        console.log('Room status:', data);
        this.trigger('room_status', data);
    }

    handleGameStarted(data) {
        console.log('Game started:', data);
        this.currentGame = data.game_id;
        this.trigger('game_started', data);
        this.getGameState();
    }

    handleRoundStarted(data) {
        console.log('Round started:', data);
        this.trigger('round_started', data);
    }

    handlePlayerTurn(data) {
        console.log('Player turn:', data);
        this.trigger('player_turn', data);
    }

    handleGameStateUpdate(data) {
        console.log('Game state update:', data);
        this.gameState = data.game_state;
        this.trigger('game_state_update', data);
    }

    handleGameOver(data) {
        console.log('Game over:', data);
        this.trigger('game_over', data);
    }

    handleGameState(data) {
        console.log('Game state:', data);
        this.gameState = data;
        this.trigger('game_state', data);
    }

    // Event registration
    on(event, handler) {
        if (!this.handlers[event]) {
            this.handlers[event] = [];
        }
        this.handlers[event].push(handler);
    }

    trigger(event, data) {
        if (this.handlers[event]) {
            this.handlers[event].forEach(handler => handler(data));
        }
    }

    // Room actions
    createRoom(roomData) {
        this.socket.emit('create_room', roomData);
    }

    joinRoom(roomId) {
        this.socket.emit('join_room', { room_id: roomId });
    }

    leaveRoom(roomId) {
        this.socket.emit('leave_room', { room_id: roomId });
    }

    getAvailableRooms() {
        this.socket.emit('get_available_rooms');
    }

    getRoomStatus(roomId) {
        this.socket.emit('get_room_status', { room_id: roomId });
    }

    // Game actions
    getGameState() {
        if (!this.currentGame) {
            this.trigger('error', { message: 'No active game' });
            return;
        }
        this.socket.emit('get_game_state', { game_id: this.currentGame });
    }

    submitMove(action, amount = 0) {
        if (!this.currentGame) {
            this.trigger('error', { message: 'No active game' });
            return;
        }

        // Validate move locally before sending
        if (!this.validateMove(action, amount)) {
            return;
        }

        this.socket.emit('game_action', {
            game_id: this.currentGame,
            action: action,
            amount: amount
        });
    }

    validateMove(action, amount) {
        if (!this.gameState) {
            this.trigger('error', { message: 'Game state not available' });
            return false;
        }

        // Check if it's the player's turn
        if (this.gameState.current_player !== this.getCurrentUserId()) {
            this.trigger('error', { message: 'Not your turn' });
            return false;
        }

        // Validate action
        switch (action) {
            case 'bet':
                if (amount < this.gameState.min_bet) {
                    this.trigger('error', { message: `Minimum bet is ${this.gameState.min_bet}` });
                    return false;
                }
                if (amount > this.gameState.max_bet) {
                    this.trigger('error', { message: `Maximum bet is ${this.gameState.max_bet}` });
                    return false;
                }
                break;

            case 'raise':
                const currentBet = Math.max(...Object.values(this.gameState.player_bets));
                if (amount <= currentBet) {
                    this.trigger('error', { message: `Raise must be greater than current bet of ${currentBet}` });
                    return false;
                }
                if (amount > this.gameState.max_bet) {
                    this.trigger('error', { message: `Maximum bet is ${this.gameState.max_bet}` });
                    return false;
                }
                break;

            case 'call':
                const callAmount = Math.max(...Object.values(this.gameState.player_bets));
                if (callAmount > this.getPlayerBalance()) {
                    this.trigger('error', { message: 'Insufficient balance to call' });
                    return false;
                }
                break;
        }

        return true;
    }

    // Utility methods
    getCurrentUserId() {
        // Get user ID from JWT token
        const token = this.token;
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));

        return JSON.parse(jsonPayload).user_id;
    }

    getPlayerBalance() {
        // Get player's current balance from game state
        return this.gameState?.player_balances?.[this.getCurrentUserId()] || 0;
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
    }
}

// Example usage:
/*
const gameClient = new GameClient('your-jwt-token');

// Register event handlers
gameClient.on('connected', () => {
    console.log('Connected to game server');
    gameClient.getAvailableRooms();
});

gameClient.on('game_state_update', (data) => {
    // Update UI with new game state
    updateGameUI(data.game_state);
});

gameClient.on('player_turn', (data) => {
    if (data.player_id === gameClient.getCurrentUserId()) {
        // Enable betting controls
        enableBettingControls();
    }
});

// Submit a move
gameClient.submitMove('bet', 50);
gameClient.submitMove('fold');
gameClient.submitMove('check');
*/ 