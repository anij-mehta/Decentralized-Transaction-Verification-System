import streamlit as st
import database
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import time
from datetime import datetime, timedelta
import base64
from PIL import Image
import io
import re

# Page config with favicon and expanded layout
st.set_page_config(
    page_title="Decentralized Transaction Verification System",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS
st.markdown("""
<style>
    .main {
        background-color: black;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .stButton>button {
        background-color: white;
        color: black;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #00FFFF;
        color : black;
    }
    .card {
        background-color: #00FFFF;
        color : black;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #333;
    }
    .metric-label {
        color: #666;
        font-size: 0.9rem;
    }
    .hash-text {
        font-family: monospace;
        overflow-wrap: break-word;
    }
    .footer {
        text-align: center;
        padding: 1rem;
        font-size: 0.8rem;
        color: black;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database connection
conn = database.get_db_connection()
cursor = conn.cursor(dictionary=True)

# Initialize session state variables
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "theme" not in st.session_state:
    st.session_state.theme = "light"
if "notification" not in st.session_state:
    st.session_state.notification = None
if "last_activity" not in st.session_state:
    st.session_state.last_activity = datetime.now()

# Check session timeout (15 minutes)
if st.session_state.user_id and (datetime.now() - st.session_state.last_activity) > timedelta(minutes=15):
    st.session_state.user_id = None
    st.session_state.notification = "Session timed out. Please log in again."

# Update last activity timestamp
st.session_state.last_activity = datetime.now()

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to validate email
def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

# Function to export transactions to CSV
def get_download_link(df, filename, text):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

# Function to get blockchain statistics
def get_blockchain_stats():
    cursor.execute("SELECT COUNT(*) as block_count FROM Blocks")
    block_count = cursor.fetchone()['block_count']
    
    cursor.execute("SELECT COUNT(*) as tx_count FROM Transactions")
    tx_count = cursor.fetchone()['tx_count']
    
    cursor.execute("SELECT COUNT(*) as user_count FROM Users")
    user_count = cursor.fetchone()['user_count']
    
    cursor.execute("SELECT SUM(amount) as volume FROM Transactions")
    result = cursor.fetchone()
    volume = result['volume'] if result['volume'] else 0
    
    return {
        "blocks": block_count,
        "transactions": tx_count,
        "users": user_count,
        "volume": volume
    }

# Sidebar for navigation
with st.sidebar:
    st.title("Decentralized Transaction Verification System")
    
    st.markdown("---")
    
    # Menu options based on login state
    if st.session_state.user_id is None:
        menu = ["Home", "Login", "Register"]
    else:
        # Get username for display
        cursor.execute("SELECT name FROM Users WHERE user_id = %s", (st.session_state.user_id,))
        user = cursor.fetchone()
        st.markdown(f"### Welcome, {user['name']}!")
        
        menu = [
            "Dashboard", 
            "My Transactions",
            "Make Transaction", 
            "My Wallets",
            "Block Explorer",
            "Profile Settings",
            "Logout"
        ]
    
    choice = st.radio("Navigation", menu)
    
    st.markdown("---")
    
    # Display some blockchain stats in sidebar
    if st.session_state.user_id is not None:
        stats = get_blockchain_stats()
        st.markdown("### Network Statistics")
        st.markdown(f"**Blocks:** {stats['blocks']}")
        st.markdown(f"**Transactions:** {stats['transactions']}")
        st.markdown(f"**Total Users:** {stats['users']}")
        st.markdown(f"**Transaction Volume:** ${stats['volume']:,.2f}")
    
    st.markdown("---")
    st.markdown("<div class='footer'>© Decentralized Transaction Verification System</div>", unsafe_allow_html=True)

# Display notification if exists
if st.session_state.notification:
    st.warning(st.session_state.notification)
    st.session_state.notification = None

# HOME PAGE
if choice == "Home":
    st.title("Welcome to the Decentralized Transaction Verification System")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="card">
            <h2>Secure Blockchain Transactions</h2>
            <p>Our platform offers a secure and transparent way to manage your digital transactions using blockchain technology.</p>
            <p>Key features:</p>
            <ul>
                <li>Real-time transaction verification</li>
                <li>Secure wallet management</li>
                <li>Detailed blockchain explorer</li>
                <li>Analytics and reporting</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="card">
            <h3>Recent Transactions</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Display recent transactions
        cursor.execute("""
            SELECT t.transaction_hash, t.amount, 
                   s.name as sender, r.name as receiver, 
                   t.timestamp
            FROM Transactions t
            JOIN Wallets ws ON t.sender_wallet_id = ws.wallet_id
            JOIN Users s ON ws.user_id = s.user_id
            JOIN Wallets wr ON t.receiver_wallet_id = wr.wallet_id
            JOIN Users r ON wr.user_id = r.user_id
            ORDER BY t.timestamp DESC LIMIT 5
        """)
        recent_txs = cursor.fetchall()
        
        if recent_txs:
            tx_df = pd.DataFrame(recent_txs)
            tx_df['transaction_hash'] = tx_df['transaction_hash'].apply(lambda x: x[:8] + '...' + x[-8:])
            st.dataframe(tx_df, hide_index=True)
        else:
            st.info("No transactions available")
    
    with col2:
        st.markdown("""
        <div class="card">
            <h3>Get Started</h3>
            <p>Create an account or login to start exploring the blockchain.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="card">
            <h3>Block Height</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Display current block height
        cursor.execute("SELECT MAX(block_id) as height FROM Blocks")
        height = cursor.fetchone()['height'] or 0
        st.markdown(f"<div class='metric-value'>{height}</div>", unsafe_allow_html=True)
        
        # Display latest block time
        cursor.execute("SELECT timestamp FROM Blocks ORDER BY block_id DESC LIMIT 1")
        latest = cursor.fetchone()
        if latest:
            latest_time = latest['timestamp']
            st.markdown(f"<div class='metric-label'>Latest block: {latest_time}</div>", unsafe_allow_html=True)
        

# LOGIN PAGE
elif choice == "Login":
    st.title("Login to Your Account")
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if not email or not password:
                st.error("Please fill in all fields")
            else:
                hashed_pw = hash_password(password)
                cursor.execute("SELECT user_id, name FROM Users WHERE email=%s AND password=%s", (email, hashed_pw))
                user = cursor.fetchone()
                
                if user:
                    st.session_state.user_id = user['user_id']
                    st.success(f"Welcome back, {user['name']}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid email or password")
    
    st.markdown("Don't have an account? Navigate to Register from the sidebar.")

# REGISTER PAGE
elif choice == "Register":
    st.title("Create a New Account")
    
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Username")
            email = st.text_input("Email")
        
        with col2:
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
        
        submit = st.form_submit_button("Register")
        
        if submit:
            # Form validation
            if not name or not email or not password or not confirm_password:
                st.error("Please fill in all fields")
            elif not is_valid_email(email):
                st.error("Please enter a valid email address")
            elif password != confirm_password:
                st.error("Passwords do not match")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters long")
            else:
                try:
                    hashed_pw = hash_password(password)
                    cursor.execute("INSERT INTO Users (name, email, password) VALUES (%s, %s, %s)", 
                                  (name, email, hashed_pw))
                    conn.commit()
                    
                    # Get the new user's ID
                    cursor.execute("SELECT user_id FROM Users WHERE email = %s", (email,))
                    user_id = cursor.fetchone()['user_id']
                    
                    # Create a wallet for the new user
                    cursor.execute("INSERT INTO Wallets (user_id, balance) VALUES (%s, %s)", 
                                  (user_id, 100.0))  # Starting balance of 100
                    conn.commit()
                    
                    st.success("Account created successfully! You can now log in.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Registration failed: {e}")

# DASHBOARD PAGE
elif choice == "Dashboard" and st.session_state.user_id:
    st.title("Your Dashboard")
    
    # Get user info
    cursor.execute("SELECT name FROM Users WHERE user_id = %s", (st.session_state.user_id,))
    user = cursor.fetchone()
    
    # Get user's wallet balance - this is correct, it's just summing up the actual balances
    cursor.execute("SELECT SUM(balance) as total_balance FROM Wallets WHERE user_id = %s", 
                   (st.session_state.user_id,))
    balance = cursor.fetchone()['total_balance'] or 0
    
    # Get user's transaction count - but we need to make sure we're not double counting
    # Modified query to prevent double counting when both sender and receiver are the same user
    cursor.execute("""
        SELECT COUNT(DISTINCT t.transaction_id) as tx_count 
        FROM Transactions t
        JOIN Wallets w ON t.sender_wallet_id = w.wallet_id OR t.receiver_wallet_id = w.wallet_id
        WHERE w.user_id = %s
    """, (st.session_state.user_id,))
    tx_count = cursor.fetchone()['tx_count']
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="card">
            <div class="metric-label">Total Balance</div>
            <div class="metric-value">$%.2f</div>
        </div>
        """ % balance, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <div class="metric-label">Transactions</div>
            <div class="metric-value">%d</div>
        </div>
        """ % tx_count, unsafe_allow_html=True)
    
    with col3:
        # Fix the total sent calculation to handle internal transfers
        cursor.execute("""
            SELECT SUM(amount) as sent 
            FROM Transactions t
            JOIN Wallets ws ON t.sender_wallet_id = ws.wallet_id
            LEFT JOIN Wallets wr ON t.receiver_wallet_id = wr.wallet_id
            WHERE ws.user_id = %s AND (wr.user_id IS NULL OR wr.user_id != %s)
        """, (st.session_state.user_id, st.session_state.user_id))
        sent_external = cursor.fetchone()['sent'] or 0
        
        # Add internal transfers as a separate calculation to avoid double counting
        cursor.execute("""
            SELECT SUM(amount) as sent_internal
            FROM Transactions t
            JOIN Wallets ws ON t.sender_wallet_id = ws.wallet_id
            JOIN Wallets wr ON t.receiver_wallet_id = wr.wallet_id
            WHERE ws.user_id = %s AND wr.user_id = %s
        """, (st.session_state.user_id, st.session_state.user_id))
        sent_internal = cursor.fetchone()['sent_internal'] or 0
        
        # Total sent is external transfers plus internal transfers
        sent = sent_external + sent_internal
        
        st.markdown("""
        <div class="card">
            <div class="metric-label">Total Sent</div>
            <div class="metric-value">$%.2f</div>
        </div>
        """ % sent, unsafe_allow_html=True)
    
    with col4:
        # Fix the total received calculation similarly
        cursor.execute("""
            SELECT SUM(amount) as received 
            FROM Transactions t
            JOIN Wallets wr ON t.receiver_wallet_id = wr.wallet_id
            LEFT JOIN Wallets ws ON t.sender_wallet_id = ws.wallet_id
            WHERE wr.user_id = %s AND (ws.user_id IS NULL OR ws.user_id != %s)
        """, (st.session_state.user_id, st.session_state.user_id))
        received_external = cursor.fetchone()['received'] or 0
        
        # Use the same internal transfer amount calculated above
        # Total received is external transfers plus internal transfers
        received = received_external + sent_internal  # We use sent_internal since it's the same amount
        
        st.markdown("""
        <div class="card">
            <div class="metric-label">Total Received</div>
            <div class="metric-value">$%.2f</div>
        </div>
        """ % received, unsafe_allow_html=True)
    
    cursor.execute("""
        SELECT DATE(t.timestamp) as date, 
               SUM(
                   CASE 
                       -- When user is sender but not receiver (outgoing)
                       WHEN sw.user_id = %s AND rw.user_id != %s THEN -amount
                       -- When user is receiver but not sender (incoming)  
                       WHEN rw.user_id = %s AND sw.user_id != %s THEN amount
                       -- When user is both sender and receiver (internal), don't count
                       ELSE 0
                   END
               ) as net_flow
        FROM Transactions t
        JOIN Wallets sw ON t.sender_wallet_id = sw.wallet_id
        JOIN Wallets rw ON t.receiver_wallet_id = rw.wallet_id
        WHERE sw.user_id = %s OR rw.user_id = %s
        GROUP BY DATE(t.timestamp)
        ORDER BY DATE(t.timestamp)
    """, (st.session_state.user_id, st.session_state.user_id, st.session_state.user_id, st.session_state.user_id, st.session_state.user_id, st.session_state.user_id))
    
    history_data = cursor.fetchall()
    
    if history_data:
        history_df = pd.DataFrame(history_data)
        
        # Create a transaction flow chart
        fig = px.line(history_df, x='date', y='net_flow', 
                       title='Daily Transaction Flow',
                       labels={'date': 'Date', 'net_flow': 'Net Flow'})
        
        # Add a horizontal line at y=0
        fig.add_shape(type='line', x0=history_df['date'].min(), x1=history_df['date'].max(),
                      y0=0, y1=0, line=dict(color='gray', width=1, dash='dash'))
        
        # Color code positive vs negative flows
        fig.update_traces(line=dict(color='green'))
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No transaction history available")
    
    # Recent activity
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="card">
            <h3>Recent Transactions</h3>
        </div>
        """, unsafe_allow_html=True)
        
        cursor.execute("""
            SELECT t.transaction_hash, t.amount, 
                   s.name as sender, r.name as receiver, 
                   t.timestamp, 
                   CASE WHEN ws.user_id = %s THEN 'Sent' ELSE 'Received' END as type
            FROM Transactions t
            JOIN Wallets ws ON t.sender_wallet_id = ws.wallet_id
            JOIN Users s ON ws.user_id = s.user_id
            JOIN Wallets wr ON t.receiver_wallet_id = wr.wallet_id
            JOIN Users r ON wr.user_id = r.user_id
            WHERE ws.user_id = %s OR wr.user_id = %s
            ORDER BY t.timestamp DESC LIMIT 5
        """, (st.session_state.user_id, st.session_state.user_id, st.session_state.user_id))
        
        user_txs = cursor.fetchall()
        
        if user_txs:
            user_tx_df = pd.DataFrame(user_txs)
            user_tx_df['transaction_hash'] = user_tx_df['transaction_hash'].apply(lambda x: x[:8] + '...' + x[-8:])
            st.dataframe(user_tx_df, hide_index=True)
        else:
            st.info("No transactions yet")
    
    with col2:
        st.markdown("""
        <div class="card">
            <h3>Your Wallets</h3>
        </div>
        """, unsafe_allow_html=True)
        
        cursor.execute("""
            SELECT wallet_id, balance, created_at 
            FROM Wallets
            WHERE user_id = %s
        """, (st.session_state.user_id,))
        
        wallets = cursor.fetchall()
        
        if wallets:
            wallet_df = pd.DataFrame(wallets)
            st.dataframe(wallet_df, hide_index=True)
        else:
            st.info("No wallets found")

# MY TRANSACTIONS PAGE
elif choice == "My Transactions" and st.session_state.user_id:
    st.title("My Transactions")
    
    # Transaction filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        tx_type = st.selectbox("Transaction Type", ["All", "Sent", "Received"])
    
    with col2:
        sort_by = st.selectbox("Sort By", ["Newest First", "Oldest First", "Amount (High to Low)", "Amount (Low to High)"])
    
    with col3:
        date_range = st.date_input("Date Range", value=[datetime.now() - timedelta(days=30), datetime.now()])
    
    # Apply filters to query
    query = """
        SELECT t.transaction_id, t.transaction_hash, t.amount, 
               s.name as sender, r.name as receiver, 
               t.timestamp, 
               CASE WHEN ws.user_id = %s THEN 'Sent' ELSE 'Received' END as type
        FROM Transactions t
        JOIN Wallets ws ON t.sender_wallet_id = ws.wallet_id
        JOIN Users s ON ws.user_id = s.user_id
        JOIN Wallets wr ON t.receiver_wallet_id = wr.wallet_id
        JOIN Users r ON wr.user_id = r.user_id
        WHERE (ws.user_id = %s OR wr.user_id = %s)
    """
    
    params = [st.session_state.user_id, st.session_state.user_id, st.session_state.user_id]
    
    # Add transaction type filter
    if tx_type == "Sent":
        query += " AND ws.user_id = %s"
        params.append(st.session_state.user_id)
    elif tx_type == "Received":
        query += " AND wr.user_id = %s"
        params.append(st.session_state.user_id)
    
    # Add date range filter
    if len(date_range) == 2:
        start_date, end_date = date_range
        end_date = end_date + timedelta(days=1)  # Include the end date
        query += " AND t.timestamp BETWEEN %s AND %s"
        params.extend([start_date, end_date])
    
    # Add sorting
    if sort_by == "Newest First":
        query += " ORDER BY t.timestamp DESC"
    elif sort_by == "Oldest First":
        query += " ORDER BY t.timestamp ASC"
    elif sort_by == "Amount (High to Low)":
        query += " ORDER BY t.amount DESC"
    elif sort_by == "Amount (Low to High)":
        query += " ORDER BY t.amount ASC"
    
    cursor.execute(query, tuple(params))
    transactions = cursor.fetchall()
    
    if transactions:
        tx_df = pd.DataFrame(transactions)
        
        # Display the transactions
        st.dataframe(tx_df, hide_index=True)
        
        # Add export button
        st.markdown(get_download_link(tx_df, "my_transactions.csv", "📥 Download Transactions as CSV"), unsafe_allow_html=True)
        
        # Create a pie chart of sent vs received
        sent_amount = sum([tx['amount'] for tx in transactions if tx['type'] == 'Sent'])
        received_amount = sum([tx['amount'] for tx in transactions if tx['type'] == 'Received'])
        
        if sent_amount > 0 or received_amount > 0:
            fig = go.Figure(data=[go.Pie(
                labels=['Sent', 'Received'],
                values=[sent_amount, received_amount],
                hole=.3,
                marker_colors=['#FF6B6B', '#4CAF50']
            )])
            
            fig.update_layout(title_text="Transaction Balance")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No transactions found matching your criteria")

# MAKE TRANSACTION PAGE
elif choice == "Make Transaction" and st.session_state.user_id:
    st.title("Send Transaction")
    
    # Initialize session states for wallet selection if not exist
    if "receiver_username" not in st.session_state:
        st.session_state.receiver_username = ""
    if "send_to_self" not in st.session_state:
        st.session_state.send_to_self = False
    if "transaction_submitted" not in st.session_state:
        st.session_state.transaction_submitted = False
    
    # Get sender's wallets
    cursor.execute("""
        SELECT w.wallet_id, w.balance 
        FROM Wallets w
        WHERE w.user_id = %s
    """, (st.session_state.user_id,))
    
    sender_wallets = cursor.fetchall()
    
    if not sender_wallets:
        st.error("You don't have any wallets. Please contact support.")
    else:
        # Get user's name
        cursor.execute("SELECT name FROM Users WHERE user_id = %s", (st.session_state.user_id,))
        user = cursor.fetchone()
        sender_name = user['name']
        
        # Create two sections - first for recipient selection, then for transaction details
        st.markdown("### Step 1: Select Source and Destination")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Sender:** {sender_name}")
            
            # Select wallet if multiple
            if len(sender_wallets) > 1:
                wallet_options = {f"Wallet #{w['wallet_id']} (Balance: ${w['balance']:.2f})": w['wallet_id'] for w in sender_wallets}
                selected_wallet_key = st.selectbox("Select Source Wallet", list(wallet_options.keys()))
                wallet_id = wallet_options[selected_wallet_key]
                current_balance = next(w['balance'] for w in sender_wallets if w['wallet_id'] == wallet_id)
            else:
                wallet_id = sender_wallets[0]['wallet_id']
                current_balance = sender_wallets[0]['balance']
                st.markdown(f"**Source Wallet:** Wallet #{wallet_id} (Balance: ${current_balance:.2f})")
        
        with col2:
            # Add option to send to own wallet
            st.session_state.send_to_self = st.checkbox("Send to my own wallet", value=st.session_state.send_to_self)
            
            if st.session_state.send_to_self:
                # Get user's other wallets (exclude the selected source wallet)
                other_wallets = [w for w in sender_wallets if w['wallet_id'] != wallet_id]
                
                if not other_wallets:
                    st.error("You don't have any other wallets to send to. Please create another wallet first.")
                    receiver_wallet_id = None
                else:
                    receiver_wallet_options = {f"Wallet #{w['wallet_id']} (Balance: ${w['balance']:.2f})": w['wallet_id'] for w in other_wallets}
                    selected_receiver_wallet_key = st.selectbox("Select Destination Wallet", list(receiver_wallet_options.keys()))
                    receiver_wallet_id = receiver_wallet_options[selected_receiver_wallet_key]
                    receiver_username = sender_name  # Same as sender
            else:
                # Receiver details
                receiver_username = st.text_input("Recipient Username", value=st.session_state.receiver_username)
                st.session_state.receiver_username = receiver_username
                
                receiver_wallet_id = None  # Initialize as None
                if receiver_username:
                    # Verify receiver exists
                    cursor.execute("SELECT user_id FROM Users WHERE name = %s", (receiver_username,))
                    receiver = cursor.fetchone()
                    
                    if receiver:
                        if receiver['user_id'] == st.session_state.user_id:
                            st.warning("This is your own username. Consider using the 'Send to my own wallet' option instead.")
                        
                        # Get receiver's wallets
                        cursor.execute("""
                            SELECT wallet_id, balance 
                            FROM Wallets 
                            WHERE user_id = %s
                        """, (receiver['user_id'],))
                        
                        receiver_wallets = cursor.fetchall()
                        
                        if receiver_wallets:
                            # Let user select which wallet to send to
                            receiver_wallet_options = {f"Wallet #{w['wallet_id']} (Balance: ${w['balance']:.2f})": w['wallet_id'] for w in receiver_wallets}
                            selected_receiver_wallet_key = st.selectbox("Select Recipient's Wallet", list(receiver_wallet_options.keys()))
                            receiver_wallet_id = receiver_wallet_options[selected_receiver_wallet_key]
                        else:
                            st.error("Recipient does not have any wallets")
                    else:
                        st.error("Recipient not found")
        
        st.markdown("---")
        st.markdown("### Step 2: Transaction Details")
        
        # Now create the form for the actual transaction
        with st.form("transaction_form"):
            # Start with 0 instead of 0.01
            amount = st.number_input("Amount", min_value=0.00, max_value=float(current_balance), value=0.00, format="%.2f")
            memo = st.text_input("Memo (Optional)", max_chars=100)
            
            # Hidden fields to store the selected wallet IDs
            st.markdown(f"From Wallet #{wallet_id} to {'your own ' if st.session_state.send_to_self else ''}Wallet #{receiver_wallet_id if receiver_wallet_id else 'unknown'}")
            
            # Add a confirmation checkbox
            confirm_transaction = st.checkbox("I confirm this transaction is correct")
            
            submit = st.form_submit_button("Send Transaction")
            
            if submit:
                if not receiver_wallet_id:
                    st.error("Please select a valid recipient wallet")
                elif amount <= 0:
                    st.error("Amount must be greater than 0")
                elif amount > current_balance:
                    st.error("Insufficient balance")
                elif not confirm_transaction:
                    st.error("Please confirm your transaction before sending")
                else:
                    st.session_state.transaction_submitted = True
                    try:
                        # Use individual statements with proper transaction management
                        try:
                            # Start transaction
                            conn.autocommit = False
                            
                            # Generate transaction hash
                            tx_hash = hashlib.sha256(f"{wallet_id}{receiver_wallet_id}{amount}{time.time()}".encode()).hexdigest()
                            
                            # Create transaction record
                            cursor.execute("""
                                INSERT INTO Transactions 
                                (transaction_hash, sender_wallet_id, receiver_wallet_id, amount, memo) 
                                VALUES (%s, %s, %s, %s, %s)
                            """, (tx_hash, wallet_id, receiver_wallet_id, amount, memo))
                            
                            # Commit transaction
                            conn.commit()
                            
                            # In Make Transaction section, modify the confirmation message:
                            recipient_display = sender_name if st.session_state.send_to_self else receiver_username
                            if st.session_state.send_to_self:
                                st.success(f"Successfully transferred ${amount:.2f} between your wallets (Wallet #{wallet_id} → Wallet #{receiver_wallet_id})")
                            else:
                                st.success(f"Successfully sent ${amount:.2f} to {recipient_display}'s Wallet #{receiver_wallet_id}")
                            
                            # Show animation of successful transaction
                            st.balloons()
                            
                        except Exception as e:
                            # Rollback on error
                            conn.rollback()
                            raise e
                        finally:
                            # Reset autocommit
                            conn.autocommit = True
                            
                    except Exception as e:
                        st.error(f"Transaction failed: {e}")
                        
        # Add a separate transaction confirmation area
        if st.session_state.transaction_submitted:
            st.session_state.transaction_submitted = False  # Reset after displaying

# MY WALLETS PAGE
elif choice == "My Wallets" and st.session_state.user_id:
    st.title("My Wallets")
    
    # Get user's wallets
    cursor.execute("""
        SELECT wallet_id, balance, created_at 
        FROM Wallets
        WHERE user_id = %s
    """, (st.session_state.user_id,))
    
    wallets = cursor.fetchall()
    
    # Display wallets
    if wallets:
        for wallet in wallets:
            with st.container():
                st.markdown(f"""
                <div class="card">
                    <h3>Wallet #{wallet['wallet_id']}</h3>
                    <div class="metric-value">${wallet['balance']:.2f}</div>
                    <div class="metric-label">Created: {wallet['created_at']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Get wallet transaction history
                cursor.execute("""
                    SELECT transaction_id, amount, timestamp,
                           CASE 
                               WHEN sender_wallet_id = %s THEN 'Outgoing'
                               ELSE 'Incoming'
                           END as direction
                    FROM Transactions
                    WHERE sender_wallet_id = %s OR receiver_wallet_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 5
                """, (wallet['wallet_id'], wallet['wallet_id'], wallet['wallet_id']))
                
                wallet_txs = cursor.fetchall()
                
                if wallet_txs:
                    wallet_tx_df = pd.DataFrame(wallet_txs)
                    st.dataframe(wallet_tx_df, hide_index=True)
                else:
                    st.info("No transactions for this wallet")
    else:
        st.error("You don't have any wallets")
    
    # Option to create a new wallet
    st.markdown("---")
    if st.button("Create New Wallet"):
        try:
            cursor.execute("INSERT INTO Wallets (user_id, balance) VALUES (%s, %s)", 
                          (st.session_state.user_id, 0.0))
            conn.commit()
            st.success("New wallet created successfully!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Failed to create wallet: {e}")

# BLOCK EXPLORER PAGE
elif choice == "Block Explorer" and st.session_state.user_id:
    st.title("Block ")
    
    # Block navigation
    col1, col2 = st.columns([1, 3])
    
    with col1:
        search_type = st.selectbox("Search By", ["Block Number", "Transaction Hash"])
        
        if search_type == "Block Number":
            # Get max block id
            cursor.execute("SELECT MAX(block_id) as max_id FROM Blocks")
            max_id = cursor.fetchone()['max_id'] or 0
            
            block_id = st.number_input("Block Number", min_value=1, max_value=max_id, value=max_id)
            search = st.button("Search Block")
            
            if search:
                block_to_show = block_id
            else:
                block_to_show = max_id
        else:
            tx_hash = st.text_input("Transaction Hash")
            search = st.button("Search Transaction")
            
            block_to_show = None
            if search and tx_hash:
                cursor.execute("SELECT block_id FROM Transactions WHERE transaction_hash = %s", (tx_hash,))
                result = cursor.fetchone()
                if result:
                    block_to_show = result['block_id']
                    if not block_to_show:
                        st.info("This transaction is not yet included in a block")
                else:
                    st.error("Transaction not found")
    
    # Visual blockchain representation
    st.markdown("### Blockchain")
    
    # Get last 10 blocks for visualization
    cursor.execute("""
        SELECT block_id, LEFT(block_hash, 8) as short_hash, timestamp, nonce
        FROM Blocks 
        ORDER BY block_id DESC
        LIMIT 10
    """)
    recent_blocks = cursor.fetchall()
    
    if recent_blocks:
        # Display blocks as connected cards
        cols = st.columns(min(5, len(recent_blocks)))
        for i, block in enumerate(recent_blocks[:5]):
            with cols[i]:
                st.markdown(f"""
                <div class="card" style="text-align: center; cursor: pointer;" onclick="alert('Block #{block['block_id']}')">
                    <div style="font-size: 1.5rem;">#{block['block_id']}</div>
                    <div class="hash-text">{block['short_hash']}...</div>
                    <div class="metric-label">{block['timestamp'].strftime('%m/%d %H:%M')}</div>
                </div>
                """, unsafe_allow_html=True)
    
    # Block details
    if block_to_show:
        st.markdown("---")
        st.markdown("### Block Details")
        
        # Get block info
        cursor.execute("""
            SELECT b.block_id, b.block_hash, b.previous_block_id, b.timestamp, b.nonce,
                   pb.block_hash as prev_hash
            FROM Blocks b
            LEFT JOIN Blocks pb ON b.previous_block_id = pb.block_id
            WHERE b.block_id = %s
        """, (block_to_show,))
        
        block = cursor.fetchone()
        
        if block:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                <div class="card">
                    <h3>Block #{block['block_id']}</h3>
                    <p><strong>Timestamp:</strong> {block['timestamp']}</p>
                    <p><strong>Nonce:</strong> {block['nonce']}</p>
                    <p><strong>Previous Block:</strong> #{block['previous_block_id'] or 'Genesis'}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="card">
                    <h3>Block Hash</h3>
                    <p class="hash-text">{block['block_hash']}</p>
                    <h3>Previous Hash</h3>
                    <p class="hash-text">{block['prev_hash'] or '0' * 64}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Get transactions in this block
            cursor.execute("""
                SELECT t.transaction_hash, t.amount, 
                       s.name as sender, r.name as receiver, 
                       t.timestamp
                FROM Transactions t
                JOIN Wallets ws ON t.sender_wallet_id = ws.wallet_id
                JOIN Users s ON ws.user_id = s.user_id
                JOIN Wallets wr ON t.receiver_wallet_id = wr.wallet_id
                JOIN Users r ON wr.user_id = r.user_id
                WHERE t.block_id = %s
                ORDER BY t.timestamp
            """, (block_to_show,))
            
            block_txs = cursor.fetchall()
            
            st.markdown("### Block Transactions")
            
            if block_txs:
                tx_df = pd.DataFrame(block_txs)
                st.dataframe(tx_df, hide_index=True)
            else:
                st.info("No transactions in this block")
        else:
            st.error("Block not found")
    
    # Optional: Blockchain integrity verification
    with st.expander("Verify Blockchain Integrity"):
        if st.button("Verify Blockchain"):
            cursor.execute("""
                SELECT block_id, block_hash, previous_block_id, nonce
                FROM Blocks
                ORDER BY block_id
            """)
            all_blocks = cursor.fetchall()
            
            valid = True
            prev_hash = None
            
            for i, block in enumerate(all_blocks):
                # For genesis block
                if i == 0 and not block['previous_block_id']:
                    prev_hash = block['block_hash']
                    continue
                
                # Check if previous hash matches
                if block['previous_block_id']:
                    prev_block_index = block['previous_block_id'] - 1  # Adjust for 0-indexing
                    if prev_block_index < len(all_blocks):
                        expected_prev_hash = all_blocks[prev_block_index]['block_hash']
                        if expected_prev_hash != prev_hash:
                            valid = False
                            break
                
                prev_hash = block['block_hash']
            
            if valid:
                st.success("Blockchain integrity verified! All blocks are correctly linked.")
            else:
                st.error("Blockchain integrity check failed. Chain may be compromised.")

# PROFILE SETTINGS PAGE
elif choice == "Profile Settings" and st.session_state.user_id:
    st.title("Profile Settings")
    
    # Get user info
    cursor.execute("SELECT name, email FROM Users WHERE user_id = %s", (st.session_state.user_id,))
    user = cursor.fetchone()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="card">
            <h3>Profile Information</h3>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("profile_form"):
            name = st.text_input("Username", value=user['name'])
            email = st.text_input("Email", value=user['email'])
            
            update_profile = st.form_submit_button("Update Profile")
            
            if update_profile:
                try:
                    cursor.execute("UPDATE Users SET name = %s, email = %s WHERE user_id = %s", 
                                  (name, email, st.session_state.user_id))
                    conn.commit()
                    st.success("Profile updated successfully!")
                except Exception as e:
                    st.error(f"Failed to update profile: {e}")
    
    with col2:
        st.markdown("""
        <div class="card">
            <h3>Change Password</h3>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_new_password = st.text_input("Confirm New Password", type="password")
            
            update_password = st.form_submit_button("Change Password")
            
            if update_password:
                if not current_password or not new_password or not confirm_new_password:
                    st.error("Please fill in all password fields")
                elif new_password != confirm_new_password:
                    st.error("New passwords do not match")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters long")
                else:
                    # Verify current password
                    hashed_current = hash_password(current_password)
                    cursor.execute("SELECT user_id FROM Users WHERE user_id = %s AND password = %s", 
                                  (st.session_state.user_id, hashed_current))
                    
                    if cursor.fetchone():
                        try:
                            hashed_new = hash_password(new_password)
                            cursor.execute("UPDATE Users SET password = %s WHERE user_id = %s", 
                                          (hashed_new, st.session_state.user_id))
                            conn.commit()
                            st.success("Password changed successfully!")
                        except Exception as e:
                            st.error(f"Failed to update password: {e}")
                    else:
                        st.error("Current password is incorrect")
    
    # Account security settings
    st.markdown("---")
    st.markdown("""
    <div class="card">
        <h3>Security Settings</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Session Timeout")
        timeout = st.slider("Session Timeout (minutes)", min_value=5, max_value=60, value=15, step=5)
        
        if st.button("Update Timeout"):
            st.success(f"Session timeout updated to {timeout} minutes")
    
    with col2:
        st.markdown("#### Two-Factor Authentication")
        enable_2fa = st.checkbox("Enable 2FA (Preview Only)")
        
        if enable_2fa:
            st.info("Two-factor authentication feature coming soon")

# LOGOUT PAGE
elif choice == "Logout":
    st.session_state.user_id = None
    st.success("You have been logged out.")
    time.sleep(1)
    st.rerun()

# Handle Footer
st.markdown("---")
st.markdown("<div class='footer'>© Decentralized Transaction Verification System | DBS Team A15 </div>", unsafe_allow_html=True)

# Close DB connection when app is done
conn.close()
