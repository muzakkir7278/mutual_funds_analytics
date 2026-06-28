-- Day 2 Analytical SQL Queries

-- 1. Top 5 funds/fund houses by AUM
SELECT * FROM clean_03_aum_by_fund_house LIMIT 5;

-- 2. Average NAV per month
SELECT amfi_code, strftime('%Y-%m', date) AS month, AVG(nav) AS avg_nav
FROM clean_02_nav_history
GROUP BY amfi_code, strftime('%Y-%m', date)
ORDER BY month;

-- 3. SIP YoY growth / trend
SELECT * FROM clean_04_monthly_sip_inflows ORDER BY 1;

-- 4. Transactions by state
SELECT state, COUNT(*) AS transaction_count, SUM(amount) AS total_amount
FROM clean_08_investor_transactions
GROUP BY state
ORDER BY total_amount DESC;

-- 5. Funds with expense_ratio less than 1 percent
SELECT * FROM clean_07_scheme_performance WHERE expense_ratio < 1;

-- 6. Transaction summary by type
SELECT transaction_type, COUNT(*) AS transaction_count, SUM(amount) AS total_amount, AVG(amount) AS average_amount
FROM clean_08_investor_transactions
GROUP BY transaction_type;

-- 7. KYC status summary
SELECT kyc_status, COUNT(*) AS investor_count
FROM clean_08_investor_transactions
GROUP BY kyc_status;

-- 8. NAV records by scheme
SELECT amfi_code, COUNT(*) AS nav_records
FROM clean_02_nav_history
GROUP BY amfi_code
ORDER BY nav_records DESC;

-- 9. Top schemes by 1-year return
SELECT * FROM clean_07_scheme_performance ORDER BY return_1y DESC LIMIT 10;

-- 10. Sample portfolio holdings
SELECT * FROM clean_09_portfolio_holdings LIMIT 20;
