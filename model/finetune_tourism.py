import torch
import json
import numpy as np
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
from sklearn.metrics import mean_absolute_error

def compute_metrics(eval_pred):
    """
    the function takes the model's predictions and the true labels,
    scales them back to the original 0-10 range,
    and calculates the mean absolute error (MAE) between the predicted and actual values.
    The MAE is returned in a dictionary format, which can be used by the Trainer to evaluate the model's performance during training.
    :param eval_pred: tuple of (logits, labels) where logits are the model's predictions and labels are the true values.
    :return: a dictionary with the mean absolute error (MAE) between the predicted and actual values, scaled back to the original 0-10 range.
    """
    # The model was trained to predict values in the range of 0-1 (by dividing the original 0-10 scores by 10).
    logits, labels = eval_pred
    if isinstance(logits, tuple):
        logits = logits[0]
    # Scale predictions and labels back to the original 0-10 range
    predictions = logits * 10.0
    actuals = labels * 10.0
    # Calculate MAE
    mae = mean_absolute_error(actuals, predictions)
    return {"mae": mae}


def prepare_data(data_list):
    """
    the function takes a list of dictionaries (each containing a review and its associated distribution of scores)
    and prepares it for training by extracting the text and labels, normalizing the labels to a 0-1 range,
     and creating a Hugging Face Dataset object.
    :param data_list: a list of dictionaries, where each dictionary has a "review" key containing the text of the review and a "distribution" key containing a dictionary of scores for various aspects (e.g., "Romance", "Family", etc.).
     The scores in the "distribution" are expected to be in the range of 0-10, and they will be normalized to a 0-1 range for training the model.
    :return: a Hugging Face Dataset object containing the processed text and labels, ready for training a sequence classification model. The labels are normalized to a 0-1 range by dividing the original scores by 10.
    """
    texts = []
    labels = []
    label_keys = ["Romance", "Family", "Cost", "Nature", "Adventure",
                  "Culture", "Food", "Relaxation", "Service", "Accessibility"]
    # Loop through each item in the input list, extract the review text and the corresponding distribution of scores, normalize the scores to a 0-1 range, and append them to the respective lists.
    for item in data_list:
        texts.append(item["review"])
        dist = [float(item["distribution"][key]) / 10.0 for key in label_keys]
        labels.append(dist)

    # Create the dataset
    dataset = Dataset.from_dict({"text": texts, "labels": labels})
    return dataset

def tokenize_function(examples, tokenizer):
    """
    the function takes a batch of examples and a tokenizer,
     and applies the tokenizer to the "text" field of the examples.
     The tokenizer will convert the raw text into a format suitable for input into a transformer model,
      such as token IDs, attention masks, etc. The function also applies padding and truncation to ensure that all sequences
       are of the same length (128 tokens in this case) for efficient batch processing during training.
    :param examples: a batch of examples, where each example is expected to have a "text" field containing the review text that needs to be tokenized. The function will process this field using the provided tokenizer.
    :param tokenizer: a tokenizer object from the Hugging Face Transformers library, which will be used to convert the raw text in the "text" field of the examples into token IDs and attention masks. The tokenizer will also handle padding and truncation to ensure that all sequences are of the same length (128 tokens in this case) for efficient batch processing during training.
    :return: a dictionary containing the tokenized outputs, including input IDs, attention masks, and any other relevant fields produced by the tokenizer. The tokenized outputs will be used as input for training a transformer model on the sequence classification task.
    """
    return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)

def main(raw_json_data):
    """
    the main function orchestrates the entire process of fine-tuning
    a transformer model for sequence classification on a dataset of reviews.
    It starts by loading a pre-trained model and tokenizer,
    prepares the dataset by processing the raw JSON data,
    tokenizes the text data, and then sets up the training arguments
    and trainer to fine-tune the model.
    :param raw_json_data: a list of dictionaries, where each dictionary contains a "review" key with the text of the review and a "distribution" key with a dictionary of scores for various aspects (e.g., "Romance", "Family", etc.). This raw JSON data will be processed to create a dataset suitable for training a transformer model for sequence classification. The function will handle the entire workflow from data preparation to model training.
    :return: None. The function will fine-tune the model and save the best model checkpoint to the specified output directory ("./tourism_model") based on the evaluation metrics computed during training.
    """
    # the model for finetune
    # the model have ~141 Million parameters, and it is a good choice for fine-tuning on a dataset of 10,000 reviews, as it provides a good balance between performance and computational efficiency. The DeBERTa-v3-small model is designed to capture complex language patterns and nuances, making it suitable for tasks like sentiment analysis and regression on review data.
    model_name = "microsoft/deberta-v3-small"
    # get the tokenizer for the model
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # define the model for sequence classification with 10 labels (for the 10 aspects) and specify that it's a regression problem
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=10,
        problem_type="regression"
    )

    # send the model to the appropriate device (GPU if available, otherwise CPU) and ensure it uses float32 precision for training
    model.to(torch.float32)

    # prepare the dataset by processing the raw JSON data, which includes extracting the review text and normalizing the distribution of scores to a 0-1 range for training
    full_dataset = prepare_data(raw_json_data)

    # split the dataset into training and testing sets (90% for training and 10% for testing) and apply the tokenization function to the text data in a batched manner for efficient processing during training
    tokenized_datasets = full_dataset.train_test_split(test_size=0.1).map(
        lambda x: tokenize_function(x, tokenizer), batched=True
    )

    # set the format of the tokenized datasets to PyTorch tensors, specifying that the "input_ids", "attention_mask", and "labels" fields should be included in the output for training the model
    tokenized_datasets.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

    # define the training arguments for fine-tuning the model, including the output directory for saving the model checkpoints, evaluation and saving strategies, learning rate, batch size, number of training epochs, weight decay, and whether to load the best model at the end of training based on evaluation metrics
    training_args = TrainingArguments(
        output_dir="./tourism_model",
        eval_strategy="epoch",
        save_strategy="epoch",
        fp16=False,
        bf16=False,
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        num_train_epochs=5,
        save_total_limit=1,
        weight_decay=0.01,
        load_best_model_at_end=True,
    )

    # define the Trainer object, which will handle the training loop, evaluation, and saving of model checkpoints based on the specified training arguments and the tokenized datasets for training and evaluation. The compute_metrics function will be used to evaluate the model's performance during training by calculating the mean absolute error (MAE) between the predicted and actual values.
    trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["test"],
    compute_metrics=compute_metrics
    )

    # train the model using the Trainer, which will handle the entire training process, including forward and backward passes, optimization, evaluation, and saving of model checkpoints based on the specified training arguments and evaluation metrics.
    trainer.train()

def second_fine_tune(new_data):
    # load the previously fine-tuned model from the checkpoint
    model_path = "./tourism_model/checkpoint-2252"
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)

    # prepare the new dataset and tokenize it using the same tokenizer as the original model.
    full_dataset = prepare_data(new_data)
    tokenized_datasets = full_dataset.train_test_split(test_size=0.1).map(
        lambda x: tokenize_function(x, tokenizer), batched=True
    )
    tokenized_datasets.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

    # define new training arguments.
    training_args = TrainingArguments(
        output_dir="./tourism_model_refined",
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=1e-5, # lower learning rate
        per_device_train_batch_size=16,
        num_train_epochs=3,  # less epochs to prevent overfitting on the new data
        weight_decay=0.05,  # more weight decay to regularize the model
        load_best_model_at_end=True,
        save_total_limit=1
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["test"],
        compute_metrics=compute_metrics
    )

    trainer.train()

# Usage
# main(raw_data)
if __name__ == "__main__":
    with open('travel_edge_reviews_1500.json', 'r') as f:
        raw_data = json.load(f)
    second_fine_tune(raw_data)
    pass