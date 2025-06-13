class GameWebSocket {
    constructor(token) {
        this.token = token;
        this.socket = null;
        this.connected = false;
        this.eventHandlers = {};
    }

    connect() {
        // Connect to WebSocket server with authentication token
        this.socket = io(window.location.origin, {
            query: {
                token: `Bearer ${this.token}`
            }
        });

        // Set up event listeners
        this.socket.on('connect', () => {
            console.log('Connected to WebSocket server');
            this.connected = true;
            this.trigger('connect');
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from WebSocket server');
            this.connected = false;
            this.trigger('disconnect');
        });

        this.socket.on('error', (error) => {
            console.error('WebSocket error:', error);
            this.trigger('error', error);
        });

        // Game-specific events
        this.socket.on('room_update', (data) => {
            console.log('Room update:', data);
            this.trigger('room_update', data);
        });

        this.socket.on('game_update', (data) => {
            console.log('Game update:', data);
            this.trigger('game_update', data);
        });

        this.socket.on('user_update', (data) => {
            console.log('User update:', data);
            this.trigger('user_update', data);
        });

        this.socket.on('room_joined', (data) => {
            console.log('Room joined:', data);
            this.trigger('room_joined', data);
        });

        this.socket.on('room_left', (data) => {
            console.log('Room left:', data);
            this.trigger('room_left', data);
        });
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
    }

    joinRoom(roomId) {
        if (!this.connected) {
            throw new Error('Not connected to WebSocket server');
        }
        this.socket.emit('join_room', { room_id: roomId });
    }

    leaveRoom(roomId) {
        if (!this.connected) {
            throw new Error('Not connected to WebSocket server');
        }
        this.socket.emit('leave_room', { room_id: roomId });
    }

    makeGameAction(gameId, actionType, data) {
        if (!this.connected) {
            throw new Error('Not connected to WebSocket server');
        }
        this.socket.emit('game_action', {
            game_id: gameId,
            action_type: actionType,
            ...data
        });
    }

    on(event, handler) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(handler);
    }

    off(event, handler) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event] = this.eventHandlers[event].filter(h => h !== handler);
        }
    }

    trigger(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(handler => handler(data));
        }
    }
}

// Example usage:
/*
const ws = new GameWebSocket('your-jwt-token');

// Set up event handlers
ws.on('connect', () => {
    console.log('Connected to game server');
});

ws.on('room_update', (data) => {
    // Update room UI
    updateRoomDisplay(data);
});

ws.on('game_update', (data) => {
    // Update game UI
    updateGameDisplay(data);
});

ws.on('user_update', (data) => {
    // Update user UI (e.g., balance)
    updateUserDisplay(data);
});

// Connect to WebSocket server
ws.connect();

// Join a room
ws.joinRoom(123);

// Make a game action
ws.makeGameAction(456, 'bet', { amount: 100 });

// Leave a room
ws.leaveRoom(123);

// Disconnect when done
ws.disconnect();
*/ 