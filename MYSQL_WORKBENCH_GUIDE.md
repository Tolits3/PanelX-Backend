# MySQL Workbench Connection Instructions for PanelX

## Connection Details:
You'll need these details to connect MySQL Workbench to your Railway database:

### From Railway Dashboard:
1. Go to your Railway project
2. Click on your MySQL service
3. Go to "Connect" tab
4. Copy the connection string

### Connection String Format:
```
mysql://username:password@host:port/database
```

### MySQL Workbench Setup:
1. Open MySQL Workbench
2. Click "+" to create new connection
3. Fill in:
   - **Connection Name**: PanelX Railway
   - **Hostname**: [from Railway connection string]
   - **Port**: [from Railway connection string, usually 3306]
   - **Username**: [from Railway connection string]
   - **Password**: Click "Store in Keychain" and enter password
   - **Default Schema**: panelx_db

## Steps to Run:

### 1. Connect to Railway MySQL
- Use the connection details from Railway dashboard
- Test connection to ensure it works

### 2. Run the Setup Script
- Open the file: `mysql_workbench_setup.sql`
- Copy and paste the entire script into MySQL Workbench query editor
- Execute the script (lightning bolt icon)

### 3. Verify Setup
After running, you should see:
- All tables created
- Test data inserted
- No error messages

### 4. Update .env file
Add your Railway DATABASE_URL to `.env`:
```
DATABASE_URL=mysql://username:password@host:port/panelx_db
```

## Common Issues:
- **Connection refused**: Check hostname/port from Railway
- **Access denied**: Verify username/password
- **Database not found**: Ensure `panelx_db` is created first

## Test Queries:
```sql
-- Check if tables exist
SHOW TABLES;

-- Check test data
SELECT * FROM users;
SELECT * FROM series;
```

Your database will be ready for the optimized backend!
