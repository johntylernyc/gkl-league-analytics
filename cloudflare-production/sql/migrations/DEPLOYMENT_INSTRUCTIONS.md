# Transaction Timestamps Migration

## Steps to Deploy

1. First, add the timestamp column:
   ```bash
   npx wrangler d1 execute gkl-fantasy --file=./sql/migrations/add_timestamp_column_1754072288.sql --remote
   ```

2. Then update existing transactions with timestamps:
   ```bash
   npx wrangler d1 execute gkl-fantasy --file=./sql/migrations/update_transaction_timestamps_1754072288.sql --remote
   ```

3. Update the Workers API to include timestamp in responses

4. Deploy the updated Workers code

5. Test the frontend to verify relative timestamps are working
