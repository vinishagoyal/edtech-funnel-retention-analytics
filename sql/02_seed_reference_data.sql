-- Reference values used by the synthetic data generator and analysis.
-- These tables are intentionally not created as hard constraints so the project
-- stays easy to extend for portfolio experimentation.

SELECT 'Organic' AS acquisition_channel
UNION ALL SELECT 'Google Ads'
UNION ALL SELECT 'Instagram'
UNION ALL SELECT 'Referral'
UNION ALL SELECT 'YouTube'
UNION ALL SELECT 'School Partnership';

