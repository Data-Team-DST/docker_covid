"""Callback Keras pour logger les métriques dans MLflow au fil de l'entraînement.

mlflow.keras.autolog() a été évalué et écarté : sur un entraînement en plusieurs
phases avec des model.fit() successifs dans le même run (cf. train_segmentation.py,
phase freeze puis fine-tune), il tente de relogger le paramètre "epochs" avec une
valeur différente à la 2e phase, ce que MLflow interdit (MlflowException avalée en
warning) — la 2e phase se retrouve alors silencieusement non trackée. Ce callback,
plus simple, ne logue que les métriques (jamais les paramètres) donc n'a pas ce
problème, et permet un décalage de step explicite pour enchaîner plusieurs phases
sur une timeline continue.
"""

import mlflow
import tensorflow as tf


class MlflowEpochLogger(tf.keras.callbacks.Callback):
    """Logue les métriques de chaque epoch dans MLflow (loss, val_loss, etc.),
    au lieu d'un seul résumé après la fin de l'entraînement — permet de suivre
    la progression en temps réel dans l'UI MLflow pendant que le run tourne.
    """

    def __init__(self, step_offset: int = 0):
        super().__init__()
        self.step_offset = step_offset

    def on_epoch_end(self, epoch, logs=None):
        """Logue les métriques Keras de l'epoch courante au step step_offset + epoch."""
        if logs:
            mlflow.log_metrics(logs, step=self.step_offset + epoch)
