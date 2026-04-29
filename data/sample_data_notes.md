# Synthetic Data Notes

This project uses only synthetic data generated with Python, Faker, and deterministic product-behavior rules. It does not contain real student, tutor, company, payment, or confidential data.

The generator creates realistic but fake EdTech product behavior:

- Some installed users never complete signup.
- Some signed-up users never submit a question.
- Math and Physics have higher demand than other subjects.
- Longer tutor wait time increases abandonment probability.
- Completed first sessions improve repeat usage probability.
- Higher session ratings increase payment conversion probability.
- Acquisition channel affects conversion and monetization.

Generated CSV files are written to `data/generated/` and are intentionally ignored by Git so the repository stays lightweight.

