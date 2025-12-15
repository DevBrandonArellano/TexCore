# This file is intentionally left blank.
# The previous signal handler in this file (debit_inventory_on_production_completion)
# contained obsolete logic that is now handled by the API view for registering production lots.
# Keeping the old signal would cause conflicts and duplicate inventory transactions.