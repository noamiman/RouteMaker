import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


def load_and_predict(text, model_path):
    tokenizer = AutoTokenizer.from_pretrained("microsoft/deberta-v3-small")
    model = AutoModelForSequenceClassification.from_pretrained(model_path)

    model.eval()

    # 2) Tokenize input text.
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=128)

    # 3) Run model inference.
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits

    # 4) Rescale outputs back to the 0-10 range.
    predictions = torch.clamp(logits * 10.0, min=0.0, max=10.0)

    # Label keys in the same order used during training.
    label_keys = ["Romance", "Family", "Cost", "Nature", "Adventure",
                  "Culture", "Food", "Relaxation", "Service", "Accessibility"]

    # Map predictions to labels.
    results = dict(zip(label_keys, predictions[0].tolist()))
    return results


# --- Example usage ---
checkpoint_path = "tourism_model_checkpoint_2240"  # Path to the local checkpoint directory.
sample_review = """
was okay very shallow but food was better - its a maybe i dont know"""

prediction = load_and_predict(sample_review, checkpoint_path)

print("Predictions (0-10):")
for label, score in prediction.items():
    print(f"{label}: {round(score)}")
