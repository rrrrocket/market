# ERP integration

Market is a decision-support producer, not an execution system.

The future boundary emits a `DistributionPlan` containing product identity, destination, channel, selected supplier offer, target price, expected cost, opportunity ID, and evidence IDs. The ERP alone owns listing, pricing, procurement, inventory, advertising, orders, payments, and transactions.

ERP outcomes return through an idempotent outcome contract: action, period, source, GMV, orders, profit, margin, conversion, and return rate. `opportunity_outcomes` stores those facts for later validation of score quality. Market never grants its administrator permissions to ERP and never directly changes Supplier records.
