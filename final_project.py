# Import necessary libraries
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score, roc_auc_score
import streamlit as st
import requests
from github import Github
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, log_loss, confusion_matrix, classification_report, roc_auc_score, mean_squared_error

# Load the dataset
file_path = "predictive_maintenance_p1.csv"  # Replace with your file path
try:
    # Explicitly specify the data types for each column
    # You may need to adjust the dtypes dictionary based on the actual data types in your CSV
    dtypes = {
        'Product ID': str,
        'Type': str,
        'Air temperature [K]': float,
        'Process temperature [K]': float,
        'Rotational speed [rpm]': int,
        'Torque [Nm]': float,
        'Tool wear [min]': int,
        'Failure Type_No Failure': int,  # Change int to 'Int64' if NaNs are present
        'Failure Type_Overstrain Failure': int,
        'Failure Type_Power Failure': int,
        'Failure Type_Random Failures': int,
        'Failure Type_Tool Wear Failure': int
    }
    data = pd.read_csv(file_path, dtype=dtypes, encoding='utf-8') # Add encoding='utf-8'
    print("Dataset successfully loaded!")

    # Check data types of each column after loading
    print(data.dtypes)

    # Check for missing values (NaN) in each column
    print(data.isnull().sum())

    # Compare the first few rows of the DataFrame with the CSV file
    print("First 5 rows of the DataFrame:")
    print(data.head())

    # Read the first few lines of the CSV file and print them
    with open(file_path, 'r', encoding='utf-8') as f:
        for i in range(5):
            print(f.readline().strip())

except FileNotFoundError:
    raise FileNotFoundError(f"Error: File not found at {file_path}. Please check the path and try again.")

# Data Cleaning and Preprocessing
data = data.drop(columns=['UDI'], axis=1)  # Drop non-predictive columns
data.fillna(data.median(numeric_only=True), inplace=True)  # Handle missing numeric values

print(data.head())

# Ensure the target column (Failure) is in the right format
# If it's not already, convert it to an integer (0 or 1) to reflect failure/no failure
if 'Target' not in data.columns:
    raise ValueError("No 'Target' column found in the dataset.")
else:
    data['Target'] = data['Target'].astype(int)  # Ensure target is int (0 or 1)

# Load the dataset
data = pd.read_csv(file_path)

# Preprocess the data
data = data.drop(columns=['UDI', 'Failure Type', 'Product ID'], errors='ignore')  # Drop unnecessary columns
data = pd.get_dummies(data, columns=['Type'], drop_first=True)  # One-hot encode the 'Type' column

# Separate features and target variable
X = data.drop(columns=['Target'], errors='ignore')
y = data['Target']

# Split the data into training, validation, and test sets
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.4, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

profit_matrix = {
       (0, 0): 0,  # True Negative (Predicted No Failure, Actual No Failure)
       (0, 1): -5750,  # False Negative (Predicted No Failure, Actual Failure) - companies lose an average of $260k per hour of machine downtime, and with 5,000 machines, that comes to $52/hour/machine. Repairs can take between hours and a week. We used a middle value of 3 days, plus $2,000 emergency reactive repair cost
       (1, 0): -465,  # False Positive (Predicted Failure, Actual No Failure), cost for trained technician to perform 2 hour inspection on machine, plus two hours of downtime for the machine
       (1, 1): 500  # True Positive (Predicted Failure, Actual Failure) - while there is still a cost associated, the emergency maintenance cost saved and downtime significantly reduced is well worth it
   }


dt_model = DecisionTreeClassifier(
    random_state=42,
    min_samples_split=10,  # Minimum samples needed to split
    min_samples_leaf=24,  # Minimum samples per leaf
    class_weight='balanced',  # Adjust class weights based on the distribution
)

# Train a decision tree classifier
dt_model.fit(X_train, y_train)

# Evaluate the model on the validation set
y_val_pred = dt_model.predict(X_val)
y_val_prob = dt_model.predict_proba(X_val)[:, 1]  # Probability of failure

print()

# Function to calculate total profit
def calculate_profit(y_true, y_pred, profit_matrix):
    total_profit = 0
    for true, pred in zip(y_true, y_pred):
        total_profit += profit_matrix[(pred, true)]
    return total_profit

# Predict the labels
y_pred = dt_model.predict(X_test)

# Calculate profit
total_profit = calculate_profit(y_test, y_pred, profit_matrix)
print(f"Total profit from the model's predictions: ${total_profit}")

print()

print("Validation Set Metrics:")
print(confusion_matrix(y_val, y_val_pred))
print(classification_report(y_val, y_val_pred))
print(f"Accuracy: {accuracy_score(y_val, y_val_pred):.4f}")
print(f"ROC AUC: {roc_auc_score(y_val, y_val_prob):.4f}")

# Evaluate on the test set
y_test_pred = dt_model.predict(X_test)
y_test_prob = dt_model.predict_proba(X_test)[:, 1]

print("\nTest Set Metrics:")
print(confusion_matrix(y_test, y_test_pred))
print(classification_report(y_test, y_test_pred))
print(f"Accuracy: {accuracy_score(y_test, y_test_pred):.4f}")
print(f"ROC AUC: {roc_auc_score(y_test, y_test_prob):.4f}")

print()

# Calculate total expected reactive maintenance costs based on predictions
total_profit = calculate_profit(y_test, y_pred, profit_matrix)
print(f"Total reactive maintenance cost from the model's predictions: ${-total_profit}")

# Get probabilities from the model
y_prob = dt_model.predict_proba(X_test)

# Adjust the threshold (e.g., threshold = 0.6 means predicting 'failure' if the probability of failure is > 0.6)
threshold = 0.74
y_pred_adjusted = (y_prob[:, 1] > threshold).astype(int)

print()

# Calculate profit with adjusted threshold
total_profit_adjusted = calculate_profit(y_test, y_pred_adjusted, profit_matrix)
print(f"Total expected reactive maintenance cost with adjusted threshold: ${-total_profit_adjusted}")

best_profit = float('-inf')
best_threshold = 0

# Search for the threshold that maximizes profit
for threshold in np.arange(0.1, 1.0, 0.01):
    y_pred_adjusted = (y_prob[:, 1] > threshold).astype(int)
    total_profit_adjusted = calculate_profit(y_test, y_pred_adjusted, profit_matrix)
    if total_profit_adjusted > best_profit:
        best_profit = total_profit_adjusted
        best_threshold = threshold

print(f"Best threshold: {best_threshold}, Best reactive maint. cost: ${-best_profit}")

print()

# Save the model
import joblib
joblib.dump(dt_model, "decision_tree_model.pkl")
print("Model saved as 'decision_tree_model.pkl'")

# Assuming X_train, y_train, X_test, and y_test are already defined

# Train the decision tree model
model = DecisionTreeClassifier(
    random_state=42,
    min_samples_split=10,  # Minimum samples needed to split
    min_samples_leaf=24,  # Minimum samples per leaf
    class_weight='balanced',  # Adjust class weights based on the distribution
)
model.fit(X_train, y_train)

# Get the predicted probabilities for each class
y_prob = model.predict_proba(X_test)

# Define your custom threshold (e.g., 0.6)
threshold = 0.74

# Adjust predictions based on the threshold
y_pred_adjusted = (y_prob[:, 1] > threshold).astype(int)

# Now y_pred_adjusted contains the predictions using the custom threshold
print("Adjusted predictions:", y_pred_adjusted)

# You can now calculate the profit or evaluate the model based on these predictions
total_profit_adjusted = calculate_profit(y_test, y_pred_adjusted, profit_matrix)
print(f"Total reactive maintenance cost with adjusted threshold: ${-total_profit_adjusted}")

# Prediction Function for New Data
def predict_failures(input_file, output_file, model):
    new_data = pd.read_csv(input_file)

    # Retain Product ID and preprocess new data
    new_data_ids = new_data['Product ID']  # Retain Product ID for output
    new_data = new_data.drop(columns=['UDI', 'Failure Type', 'Product ID'], errors='ignore')
    new_data = pd.get_dummies(new_data, columns=['Type'], drop_first=True)
    new_data = new_data.reindex(columns=X_train.columns, fill_value=0)  # Align columns with training set

    # Check if columns align correctly
    if new_data.isnull().values.any():
        print("Warning: Missing values detected in the new dataset after preprocessing.")

    # Get predictions and probabilities
    predictions = model.predict(new_data)  # Binary predictions (0 or 1)
    probabilities = model.predict_proba(new_data)

    # Check if probabilities is 2D and access accordingly:
    if probabilities.ndim == 2:
        probabilities = probabilities[:, 1]  # Probability of failure (class 1)
    else:
        # If probabilities is 1D, it's already the probability of the single class
        pass  # No need to slice

    # Debugging: Print sample probabilities
    print("Sample Probabilities:", probabilities[:10])  # Check if these are decimal values

    # Apply custom threshold for classification
    threshold = 0.74  # Most effective threshold from model training
    predictions = (probabilities > threshold).astype(int)  # 1 for Failure, 0 for No Failure

    # Create a DataFrame for the new data with predictions
    new_data['Prediction'] = predictions

    # Create the results dataframe
    results = pd.DataFrame({
        'Product ID': new_data_ids,
        'Failure Predicted': predictions,
        'Failure Probability': probabilities  # Decimal probabilities
    })

    # Save the results to a CSV file
    results.to_csv(output_file, index=False)
    print(f"Predictions saved to {output_file}")

    print()
    print(new_data.head())
    print(new_data.describe())

# Predict on new dataset
input_csv = "predictive_maintenance_p2.csv"  # Replace with the path to your new dataset
output_csv = "failure_predictions.csv"
predict_failures(input_csv, output_csv, dt_model)

from sklearn.tree import export_text
print(export_text(dt_model, feature_names=list(X_train.columns)))

probabilities = dt_model.predict_proba(X_test)
print(probabilities)

# DASHBOARD CREATION

# Streamlit heading for the dashboard
st.title("Upcoming Maintenance Dashboard")

# Load the failure predictions data from the CSV file
failure_predictions = pd.read_csv('failure_predictions.csv')

# Display the columns in the predictions dataframe (just to confirm the data is loaded correctly)
st.write("Columns in the predictions data:", failure_predictions.columns)

# 1. Create the input box to type in Product ID
product_id_input = st.text_input('Enter Product ID of the machine to check failure likelihood')

# 2. Check if the entered Product ID exists in the dataset
if product_id_input:
    if product_id_input in failure_predictions['Product ID'].values:
        # Extract the row corresponding to the entered Product ID
        product_row = failure_predictions[failure_predictions['Product ID'] == product_id_input]

        # 3. Display the prediction (0 or 1) and probability
        st.write(f"Prediction for Product ID {product_id_input}:")
        st.write(f"Failure Predicted: {product_row['Failure Predicted'].values[0]}")  # Get the prediction value (0 or 1)
        st.write(f"Failure Probability: {product_row['Failure Probability'].values[0]}")  # Get the probability value
    else:
        st.write(f"Product ID {product_id_input} not found in the dataset.")

# Display the entire DataFrame
st.write("Failure Predictions DataFrame:")
st.dataframe(failure_predictions)

# 4. Display the top 25 most likely machines to experience a failure
# Sort by 'Failure Probability' and get the top 25
top_failures = failure_predictions.nlargest(25, 'Failure Probability')

# Display the top 25 most likely failures, showing Product ID, Failure Predicted, and Failure Probability
st.write("Top 25 Most Likely Machines to Experience a Failure:")
st.dataframe(top_failures[['Product ID', 'Failure Predicted', 'Failure Probability']])
