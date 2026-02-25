### 2. Email Importance & Public Interest Prediction
**Question**: What linguistic and metadata features predict high community engagement (star count) with controversial documents?

**Motivation**: Understanding what makes documents newsworthy or publicly important could help prioritize investigative resources and improve information retrieval systems for leaked/released documents.

**Approach**:
- Regression: Predict star count (0-4568)
- Classification: High interest (top 10%) vs. Low interest
- Ranking: Order emails by predicted importance

**Models**:
- Baseline: Random Forest Regressor
- Advanced: Gradient Boosting (XGBoost, LightGBM)
- Deep Learning: Transformer encoder + regression head
- Ensemble: Combine gradient boosting + BERT embeddings

**Features**:
- Subject line embeddings
- Preview text embeddings  
- Thread length (message count)
- Attachment presence
- Redaction status
- Sender identity patterns
- Temporal features (date, day of week)
- Email drop source

**Evaluation**:
- RMSE, MAE for regression
- Precision@k for top-k predictions
- NDCG for ranking quality
