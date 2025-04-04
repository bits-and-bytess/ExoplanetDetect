
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Machine learning libraries
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE
from scipy.signal import savgol_filter
from sklearn.preprocessing import normalize, RobustScaler

# Deep learning libraries
import tensorflow as tf
from tensorflow import keras 
from keras.api.models import Sequential
from keras.api.layers import Dense, Flatten, Conv1D, MaxPooling1D


class ExoplanetDetector:
    """
    A machine learning system for detecting exoplanets from NASA Kepler light curve data.
    
    This class implements a complete pipeline for processing astronomical light curves,
    training various neural network models, and evaluating their performance for the
    binary classification task of identifying stars with orbiting exoplanets.
    """
    
    def __init__(self):
        """Initialize the ExoplanetDetector with empty attributes."""
        self.df_train = None
        self.df_test = None
        self.train_X = None
        self.train_y = None
        self.test_X = None
        self.test_y = None
        self.aug_train_X = None
        self.aug_train_y = None
        self.aug_test_X = None
        self.aug_test_y = None
        self.model = None
        self.history = None
        
    def load_data(self, train_path, test_path):
        """
        Load training and testing data from CSV files.
        
        Parameters:
        -----------
        train_path : str
            Path to the training CSV file
        test_path : str
            Path to the testing CSV file
        """
        print("Loading datasets...")
        self.df_train = pd.read_csv(train_path)
        self.df_train.LABEL = self.df_train.LABEL - 1  # Adjusting labels to 0/1
        
        self.df_test = pd.read_csv(test_path)
        self.df_test.LABEL = self.df_test.LABEL - 1    # Adjusting labels to 0/1
        
        self.train_X = self.df_train.drop('LABEL', axis=1)
        self.train_y = self.df_train['LABEL'].values
        self.test_X = self.df_test.drop('LABEL', axis=1)
        self.test_y = self.df_test['LABEL'].values
        
        print(f"Loaded {len(self.train_X)} training samples and {len(self.test_X)} test samples")
        print(f"Exoplanet stars in training: {sum(self.train_y)} ({sum(self.train_y)/len(self.train_y)*100:.2f}%)")
        print(f"Exoplanet stars in testing: {sum(self.test_y)} ({sum(self.test_y)/len(self.test_y)*100:.2f}%)")
        
    def preprocess_data(self):
        """
        Apply a series of preprocessing steps to prepare light curve data for modeling:
        1. Fourier transformation
        2. Savitzky-Golay filtering
        3. Normalization
        4. Robust scaling
        5. SMOTE augmentation to balance classes
        """
        print("Preprocessing data...")
        
        # Apply Fourier transformation
        fourier_train_X, fourier_test_X = self._fourier(self.train_X, self.test_X)
        
        # Apply Savitzky-Golay filter
        savgol_train_X, savgol_test_X = self._savgol(fourier_train_X, fourier_test_X)
        
        # Normalize data
        norm_train_X, norm_test_X = self._norm(savgol_train_X, savgol_test_X)
        
        # Apply robust scaling
        robust_train_X, robust_test_X = self._robust(norm_train_X, norm_test_X)
        
        # Apply SMOTE for class balancing
        smote_train_X, smote_train_y = self._smote(robust_train_X, self.train_y)
        
        # Split the augmented data
        aug_train_X, new_X_test_data, aug_train_y, new_y_test_data = train_test_split(
            smote_train_X, smote_train_y, test_size=0.3
        )
        self.aug_train_X = aug_train_X
        self.aug_train_y = aug_train_y
        
        # Combine original test data with new test data from SMOTE
        self.aug_test_X = np.concatenate((robust_test_X, new_X_test_data), axis=0)
        self.aug_test_y = np.concatenate((self.test_y, new_y_test_data), axis=0)
        
        print(f"Preprocessed data shapes:")
        print(f"Augmented training data: {self.aug_train_X.shape}, labels: {self.aug_train_y.shape}")
        print(f"Augmented testing data: {self.aug_test_X.shape}, labels: {self.aug_test_y.shape}")
        
    def _fourier(self, df1, df2):
        """Apply Fast Fourier Transform to extract frequency domain features."""
        train_X = np.abs(np.fft.fft(df1, axis=1))
        test_X = np.abs(np.fft.fft(df2, axis=1))
        return train_X, test_X
    
    def _savgol(self, df1, df2):
        """Apply Savitzky-Golay filter to smooth the data while preserving peaks."""
        x = savgol_filter(df1, 21, 4, deriv=0)
        y = savgol_filter(df2, 21, 4, deriv=0)
        return x, y
    
    def _norm(self, df1, df2):
        """Normalize the data."""
        train_X = normalize(df1)
        test_X = normalize(df2)
        return train_X, test_X
    
    def _robust(self, df1, df2):
        """Apply robust scaling to make the model resistant to outliers."""
        scaler = RobustScaler()
        train_X = scaler.fit_transform(df1)
        test_X = scaler.transform(df2)
        return train_X, test_X
    
    def _smote(self, a, b):
        """Apply SMOTE to handle class imbalance by generating synthetic examples."""
        model = SMOTE()
        X, y = model.fit_resample(a, b)
        return X, y
    
    def build_dense_model(self):
        """
        Build a simple feedforward neural network with two dense layers.
        """
        print("Building dense neural network model...")
        model = Sequential()
        
        # Input layer with 10 neurons and ReLU activation
        model.add(Dense(10, activation='relu', input_shape=(self.aug_train_X.shape[1],)))
        
        # Output layer with sigmoid activation for binary classification
        model.add(Dense(1, activation='sigmoid'))
        
        # Compile model with binary crossentropy loss and Adam optimizer
        model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
        
        self.model = model
        print("Model summary:")
        self.model.summary()
        
    def build_cnn_model(self):
        """
        Build a 1D convolutional neural network model for time series classification.
        """
        print("Building 1D CNN model...")
        
        # Reshape data for CNN input (samples, timesteps, features)
        self.cnn_aug_train_X = np.expand_dims(self.aug_train_X, axis=2)
        self.cnn_aug_train_y = self.aug_train_y
        self.cnn_aug_test_X = np.expand_dims(self.aug_test_X, axis=2)
        self.cnn_aug_test_y = self.aug_test_y
        
        # Create sequential model
        model = Sequential()
        
        # First convolutional block
        model.add(Conv1D(8, kernel_size=5, activation='relu', padding='same', 
                         input_shape=(self.aug_train_X.shape[1], 1)))
        model.add(MaxPooling1D(pool_size=4, strides=4, padding='same'))
        
        # Second convolutional block
        model.add(Conv1D(16, kernel_size=3, activation='relu', padding='same'))
        model.add(MaxPooling1D(pool_size=4, strides=4, padding='same'))
        
        # Flatten and output layer
        model.add(Flatten())
        model.add(Dense(1, activation='sigmoid'))
        
        # Compile model
        model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
        
        self.model = model
        print("Model summary:")
        self.model.summary()
        
    def train_model(self, batch_size=64, epochs=20, use_cnn=False):
        """
        Train the current model on the augmented dataset.
        
        Parameters:
        -----------
        batch_size : int
            Number of samples per gradient update
        epochs : int
            Number of epochs to train the model
        use_cnn : bool
            Whether to use the CNN model (requires different data format)
        """
        print(f"Training model for {epochs} epochs with batch size {batch_size}...")
        
        if use_cnn:
            X_train = self.cnn_aug_train_X
            y_train = self.cnn_aug_train_y
            X_test = self.cnn_aug_test_X
            y_test = self.cnn_aug_test_y
        else:
            X_train = self.aug_train_X
            y_train = self.aug_train_y
            X_test = self.aug_test_X
            y_test = self.aug_test_y
        
        # Train the model
        self.history = self.model.fit(
            X_train, y_train,
            batch_size=batch_size,
            epochs=epochs,
            verbose=1,
            validation_data=(X_test, y_test),
            shuffle=True
        )
        
        # Evaluate the model
        performance = self.model.evaluate(X_test, y_test, batch_size=batch_size)
        print(f"Final validation loss: {performance[0]:.4f}, accuracy: {performance[1]:.4f}")
        
        return self.history, performance
    
    def evaluate_model(self, use_cnn=False):
        """
        Evaluate the trained model and display performance metrics.
        
        Parameters:
        -----------
        use_cnn : bool
            Whether to use CNN-formatted data for evaluation
        """
        if use_cnn:
            train_X = self.cnn_aug_train_X
            train_y = self.cnn_aug_train_y
            test_X = self.cnn_aug_test_X
            test_y = self.cnn_aug_test_y
        else:
            train_X = self.aug_train_X
            train_y = self.aug_train_y
            test_X = self.aug_test_X
            test_y = self.aug_test_y
            
        # Generate predictions
        train_predictions = self.model.predict(train_X)
        train_predictions = (train_predictions > 0.5)
        
        test_predictions = self.model.predict(test_X)
        test_predictions = (test_predictions > 0.5)
        
        # Calculate metrics
        train_accuracy = accuracy_score(train_y, train_predictions)
        test_accuracy = accuracy_score(test_y, test_predictions)
        
        print("\nModel Evaluation:")
        print(f"Training accuracy: {train_accuracy:.4f}")
        print(f"Testing accuracy: {test_accuracy:.4f}")
        
        print("\nClassification Report (Training):")
        print(classification_report(train_y, train_predictions))
        
        print("\nClassification Report (Testing):")
        print(classification_report(test_y, test_predictions))
        
        # Plot confusion matrices
        self._plot_confusion_matrix(train_y, train_predictions, "Training")
        self._plot_confusion_matrix(test_y, test_predictions, "Testing")
        
        # Plot training history
        self._plot_training_history()
        
    def _plot_confusion_matrix(self, y_true, y_pred, title_prefix):
        """Plot confusion matrix for model evaluation."""
        cm = confusion_matrix(y_true, y_pred)
        labels = [0, 1]
        df_cm = pd.DataFrame(cm, index=labels, columns=labels)
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(df_cm, annot=True, cmap='Blues', fmt='g')
        plt.title(f'Confusion Matrix - {title_prefix} Data')
        plt.ylabel('True label')
        plt.xlabel('Predicted label')
        plt.show()
        
    def _plot_training_history(self):
        """Plot training and validation metrics over epochs."""
        plt.figure(figsize=(15, 5))
        
        # Plot accuracy
        plt.subplot(1, 2, 1)
        plt.plot(self.history.history['accuracy'])
        plt.plot(self.history.history['val_accuracy'])
        plt.title('Model accuracy over training')
        plt.ylabel('Accuracy')
        plt.xlabel('Epoch')
        plt.legend(['Train', 'Validation'], loc='lower right')
        
        # Plot loss
        plt.subplot(1, 2, 2)
        plt.plot(self.history.history['loss'])
        plt.plot(self.history.history['val_loss'])
        plt.title('Model loss over training')
        plt.ylabel('Loss')
        plt.xlabel('Epoch')
        plt.legend(['Train', 'Validation'], loc='upper right')
        
        plt.tight_layout()
        plt.show()
        
    def save_model(self, filepath):
        """Save the trained model to disk."""
        self.model.save(filepath)
        print(f"Model saved to {filepath}")
        
    def load_model(self, filepath):
        """Load a previously trained model from disk."""
        self.model = keras.models.load_model(filepath)
        print(f"Model loaded from {filepath}")


# Example usage
if __name__ == "__main__":
    # Create detector instance
    detector = ExoplanetDetector()
    
    # Load data
    detector.load_data('exoTrain.csv', 'exoTest.csv')
    
    # Preprocess data
    detector.preprocess_data()
    
    # Build and train dense model
    detector.build_dense_model()
    history, performance = detector.train_model(batch_size=64, epochs=20)
    detector.evaluate_model()
    
    # Build and train CNN model
    detector.build_cnn_model()
    history, performance = detector.train_model(batch_size=64, epochs=20, use_cnn=True)
    detector.evaluate_model(use_cnn=True)
    
    # Save the best model
    detector.save_model('exoplanet_cnn_model.keras')
    