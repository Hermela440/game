// Admin Dashboard JavaScript

class AdminDashboard {
    constructor() {
        this.token = localStorage.getItem('token');
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.charts = {};
        this.initializeEventListeners();
        this.loadDashboardData();
    }

    initializeEventListeners() {
        // Sidebar toggle
        document.getElementById('sidebarCollapse')?.addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('active');
        });

        // Navigation links
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = e.target.getAttribute('data-section');
                this.showSection(section);
            });
        });

        // User management
        document.getElementById('editUserBtn')?.addEventListener('click', () => {
            this.editUser();
        });

        // Pagination
        document.querySelectorAll('.pagination .page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = e.target.getAttribute('data-page');
                this.changePage(page);
            });
        });
    }

    async loadDashboardData() {
        try {
            const response = await fetch('/api/admin/dashboard', {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });
            const data = await response.json();
            this.updateDashboard(data);
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showError('Failed to load dashboard data');
        }
    }

    updateDashboard(data) {
        // Update statistics cards
        this.updateStatCards(data.game_stats, data.user_stats);
        
        // Update charts
        this.updateCharts(data);
        
        // Update recent transactions
        this.updateTransactions(data.recent_transactions);
        
        // Update system status
        this.updateSystemStatus(data.system_status);
    }

    updateStatCards(gameStats, userStats) {
        // Update game statistics
        document.getElementById('totalGames').textContent = gameStats.total_games;
        document.getElementById('activeGames').textContent = gameStats.active_games;
        document.getElementById('totalBets').textContent = `$${gameStats.total_bets.toFixed(2)}`;
        document.getElementById('winRate').textContent = `${gameStats.win_rate}%`;

        // Update user statistics
        document.getElementById('totalUsers').textContent = userStats.total_users;
        document.getElementById('activeUsers').textContent = userStats.active_users;
        document.getElementById('newUsersToday').textContent = userStats.new_users_today;
        document.getElementById('newUsersWeek').textContent = userStats.new_users_week;
    }

    updateCharts(data) {
        // User Activity Chart
        const userActivityCtx = document.getElementById('userActivityChart')?.getContext('2d');
        if (userActivityCtx && !this.charts.userActivity) {
            this.charts.userActivity = new Chart(userActivityCtx, {
                type: 'line',
                data: {
                    labels: data.user_stats.user_activity.map(item => item.date),
                    datasets: [{
                        label: 'Active Users',
                        data: data.user_stats.user_activity.map(item => item.count),
                        borderColor: '#007bff',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }

        // Game Statistics Chart
        const gameStatsCtx = document.getElementById('gameStatsChart')?.getContext('2d');
        if (gameStatsCtx && !this.charts.gameStats) {
            this.charts.gameStats = new Chart(gameStatsCtx, {
                type: 'bar',
                data: {
                    labels: data.game_stats.popular_games.map(game => game.name),
                    datasets: [{
                        label: 'Games Played',
                        data: data.game_stats.popular_games.map(game => game.count),
                        backgroundColor: '#28a745'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }
    }

    updateTransactions(transactions) {
        const tbody = document.querySelector('#transactionsTable tbody');
        if (!tbody) return;

        tbody.innerHTML = transactions.map(transaction => `
            <tr>
                <td>${transaction.id}</td>
                <td>${transaction.username}</td>
                <td>${transaction.type}</td>
                <td>$${transaction.amount.toFixed(2)}</td>
                <td>${new Date(transaction.created_at).toLocaleString()}</td>
                <td>
                    <span class="badge ${this.getStatusBadgeClass(transaction.status)}">
                        ${transaction.status}
                    </span>
                </td>
            </tr>
        `).join('');
    }

    updateSystemStatus(status) {
        const statusElement = document.getElementById('systemStatus');
        if (!statusElement) return;

        statusElement.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h5 class="mb-0">System Status</h5>
                    <p class="text-muted mb-0">Last updated: ${new Date().toLocaleString()}</p>
                </div>
                <span class="badge ${this.getStatusBadgeClass(status.overall)}">
                    ${status.overall}
                </span>
            </div>
            <div class="mt-3">
                <div class="d-flex justify-content-between mb-2">
                    <span>Database</span>
                    <span class="badge ${this.getStatusBadgeClass(status.database)}">
                        ${status.database}
                    </span>
                </div>
                <div class="d-flex justify-content-between mb-2">
                    <span>WebSocket</span>
                    <span class="badge ${this.getStatusBadgeClass(status.websocket)}">
                        ${status.websocket}
                    </span>
                </div>
                <div class="d-flex justify-content-between">
                    <span>API</span>
                    <span class="badge ${this.getStatusBadgeClass(status.api)}">
                        ${status.api}
                    </span>
                </div>
            </div>
        `;
    }

    getStatusBadgeClass(status) {
        switch (status.toLowerCase()) {
            case 'online':
                return 'badge-success';
            case 'warning':
                return 'badge-warning';
            case 'offline':
                return 'badge-danger';
            default:
                return 'badge-secondary';
        }
    }

    showSection(section) {
        // Hide all sections
        document.querySelectorAll('.content-section').forEach(section => {
            section.style.display = 'none';
        });

        // Show selected section
        document.getElementById(section)?.style.display = 'block';

        // Update active nav link
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-section') === section) {
                link.classList.add('active');
            }
        });

        // Load section data
        switch (section) {
            case 'users':
                this.loadUsers();
                break;
            case 'games':
                this.loadGames();
                break;
            case 'transactions':
                this.loadTransactions();
                break;
        }
    }

    async loadUsers() {
        try {
            const response = await fetch(`/api/admin/users?page=${this.currentPage}&per_page=${this.itemsPerPage}`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });
            const data = await response.json();
            this.updateUsersTable(data);
        } catch (error) {
            console.error('Error loading users:', error);
            this.showError('Failed to load users');
        }
    }

    async loadGames() {
        try {
            const response = await fetch(`/api/admin/games?page=${this.currentPage}&per_page=${this.itemsPerPage}`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });
            const data = await response.json();
            this.updateGamesTable(data);
        } catch (error) {
            console.error('Error loading games:', error);
            this.showError('Failed to load games');
        }
    }

    async loadTransactions() {
        try {
            const response = await fetch(`/api/admin/transactions?page=${this.currentPage}&per_page=${this.itemsPerPage}`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });
            const data = await response.json();
            this.updateTransactionsTable(data);
        } catch (error) {
            console.error('Error loading transactions:', error);
            this.showError('Failed to load transactions');
        }
    }

    updateUsersTable(data) {
        const tbody = document.querySelector('#usersTable tbody');
        if (!tbody) return;

        tbody.innerHTML = data.items.map(user => `
            <tr>
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email}</td>
                <td>${user.role}</td>
                <td>$${user.balance.toFixed(2)}</td>
                <td>
                    <span class="badge ${user.is_active ? 'badge-success' : 'badge-danger'}">
                        ${user.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="adminDashboard.editUser(${user.id})">
                        Edit
                    </button>
                </td>
            </tr>
        `).join('');

        this.updatePagination(data.total, data.pages);
    }

    updateGamesTable(data) {
        const tbody = document.querySelector('#gamesTable tbody');
        if (!tbody) return;

        tbody.innerHTML = data.items.map(game => `
            <tr>
                <td>${game.id}</td>
                <td>${game.name}</td>
                <td>${game.room_id}</td>
                <td>$${game.total_bet.toFixed(2)}</td>
                <td>${game.status}</td>
                <td>${new Date(game.created_at).toLocaleString()}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="adminDashboard.viewGameDetails(${game.id})">
                        View
                    </button>
                </td>
            </tr>
        `).join('');

        this.updatePagination(data.total, data.pages);
    }

    updateTransactionsTable(data) {
        const tbody = document.querySelector('#transactionsTable tbody');
        if (!tbody) return;

        tbody.innerHTML = data.items.map(transaction => `
            <tr>
                <td>${transaction.id}</td>
                <td>${transaction.username}</td>
                <td>${transaction.type}</td>
                <td>$${transaction.amount.toFixed(2)}</td>
                <td>${new Date(transaction.created_at).toLocaleString()}</td>
                <td>
                    <span class="badge ${this.getStatusBadgeClass(transaction.status)}">
                        ${transaction.status}
                    </span>
                </td>
            </tr>
        `).join('');

        this.updatePagination(data.total, data.pages);
    }

    updatePagination(total, pages) {
        const pagination = document.querySelector('.pagination');
        if (!pagination) return;

        let html = '';
        for (let i = 1; i <= pages; i++) {
            html += `
                <li class="page-item ${i === this.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `;
        }

        pagination.innerHTML = html;
    }

    async editUser(userId) {
        try {
            const response = await fetch(`/api/admin/users/${userId}`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });
            const user = await response.json();

            // Populate modal
            document.getElementById('editUserId').value = user.id;
            document.getElementById('editUserEmail').value = user.email;
            document.getElementById('editUserRole').value = user.role;
            document.getElementById('editUserActive').checked = user.is_active;

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('editUserModal'));
            modal.show();
        } catch (error) {
            console.error('Error loading user:', error);
            this.showError('Failed to load user details');
        }
    }

    async saveUser() {
        const userId = document.getElementById('editUserId').value;
        const userData = {
            email: document.getElementById('editUserEmail').value,
            role: document.getElementById('editUserRole').value,
            is_active: document.getElementById('editUserActive').checked
        };

        try {
            const response = await fetch(`/api/admin/users/${userId}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(userData)
            });

            if (response.ok) {
                // Hide modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
                modal.hide();

                // Reload users
                this.loadUsers();
            } else {
                throw new Error('Failed to update user');
            }
        } catch (error) {
            console.error('Error updating user:', error);
            this.showError('Failed to update user');
        }
    }

    async viewGameDetails(gameId) {
        try {
            const response = await fetch(`/api/admin/games/${gameId}`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });
            const game = await response.json();

            // Populate modal
            document.getElementById('gameDetailsId').textContent = game.id;
            document.getElementById('gameDetailsName').textContent = game.name;
            document.getElementById('gameDetailsRoom').textContent = game.room_id;
            document.getElementById('gameDetailsBet').textContent = `$${game.total_bet.toFixed(2)}`;
            document.getElementById('gameDetailsStatus').textContent = game.status;
            document.getElementById('gameDetailsCreated').textContent = new Date(game.created_at).toLocaleString();

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('gameDetailsModal'));
            modal.show();
        } catch (error) {
            console.error('Error loading game details:', error);
            this.showError('Failed to load game details');
        }
    }

    showError(message) {
        // Create toast
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.innerHTML = `
            <div class="toast-header">
                <strong class="me-auto">Error</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;

        // Add toast to container
        const container = document.getElementById('toastContainer');
        if (container) {
            container.appendChild(toast);
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
        }
    }

    changePage(page) {
        this.currentPage = parseInt(page);
        const activeSection = document.querySelector('.content-section[style="display: block"]').id;
        this.showSection(activeSection);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.adminDashboard = new AdminDashboard();
}); 