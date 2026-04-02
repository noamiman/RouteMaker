import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


def load_and_predict(text, model_path):
    tokenizer = AutoTokenizer.from_pretrained("microsoft/deberta-v3-small")
    model = AutoModelForSequenceClassification.from_pretrained(model_path)

    model.eval()

    # 2. הכנת הטקסט (Tokenization)
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=128)

    # 3. הרצת המודל
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits

    # 4. עיבוד התוצאה (חזרה לסקאלה של 0-10 כפי שהגדרת ב-compute_metrics)
    predictions = torch.clamp(logits * 10.0, min=0.0, max=10.0)

    # המפתחות לפי הסדר שהגדרת ב-prepare_data
    label_keys = ["Romance", "Family", "Cost", "Nature", "Adventure",
                  "Culture", "Food", "Relaxation", "Service", "Accessibility"]

    # הצמדת התוצאות למפתחות
    results = dict(zip(label_keys, predictions[0].tolist()))
    return results


# --- שימוש ---
checkpoint_path = "tourism_model_checkpoint_2240"  # הנתיב לתיקייה מהתמונה
sample_review = """
was okay very shallow but food was better - its a maybe i dont know"""

prediction = load_and_predict(sample_review, checkpoint_path)

print("Predictions (0-10):")
for label, score in prediction.items():
    print(f"{label}: {round(score)}")
