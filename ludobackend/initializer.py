import json
import datetime
import os
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
import tensorflow as tf
from tensorflow.keras.layers import Conv1D, BatchNormalization, Dense, Activation, Add, Dense, Input, Flatten
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam, schedules, serialize
# tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)
from pathlib import Path
# from keras.utils.vis_utils import plot_model


# The following code is written exactly with reference to AlphaZero Paper
# No changes are made as of now

# We can change parameters and other stuff if needed

def residual_block(x, filters, kernel_size = 3):
    x1 = Conv1D(filters, kernel_size, padding = 'same', kernel_regularizer=tf.keras.regularizers.L2(1e-4), bias_regularizer=tf.keras.regularizers.L2(1e-4))(x)
    x1 = BatchNormalization()(x1)
    x1 = Activation('relu')(x1)

    x2 = Conv1D(filters, kernel_size, padding = 'same', kernel_regularizer=tf.keras.regularizers.L2(1e-4), bias_regularizer=tf.keras.regularizers.L2(1e-4))(x1)
    x2 = BatchNormalization()(x2)

    x = Add()([x, x2])
    x = Activation('relu')(x)

    return x

def value_head(x):
    x = Conv1D(1, 1, padding = 'same', kernel_regularizer=tf.keras.regularizers.L2(1e-4), bias_regularizer=tf.keras.regularizers.L2(1e-4))(x)
    x = BatchNormalization()(x)
    x = Activation('relu')(x)

    x = Flatten()(x)
    x = Dense(128, activation = 'relu', kernel_regularizer=tf.keras.regularizers.L2(1e-4), bias_regularizer=tf.keras.regularizers.L2(1e-4))(x)
    x = Dense(1, activation ='tanh', kernel_regularizer=tf.keras.regularizers.L2(1e-4), bias_regularizer=tf.keras.regularizers.L2(1e-4))(x)

    return x

def nn_model(input_shape):
    input_layer = Input(shape = input_shape)

    x = Conv1D(128, 3, padding = 'same', kernel_regularizer=tf.keras.regularizers.L2(1e-4), bias_regularizer=tf.keras.regularizers.L2(1e-4))(input_layer)
    x = BatchNormalization()(x)
    x = Activation('relu')(x)

    for _ in range(28):
        x = residual_block(x, 128)

    value_output = value_head(x)

    model = Model(inputs = input_layer, outputs = value_output)

    return model


if __name__ == "__main__":

    DIRECTORY = Path("runs")
    TRAIN_DIRECTORY = DIRECTORY / "run2"
    os.makedirs(TRAIN_DIRECTORY, exist_ok=True)
    dummy_schedule = schedules.PiecewiseConstantDecay(boundaries=[1,2,], values=[1e-2, 1e-3, 1e-4])
    optimizer = Adam(learning_rate=dummy_schedule)
    input_shape = (59,21)
    model = nn_model(input_shape)
    model.save(str(TRAIN_DIRECTORY / "checkpoints" / datetime.datetime.now().strftime("%Y_%b_%d_%H_%M_%S_%f")))
    model.save(str(TRAIN_DIRECTORY / "chkpts_to_elo" / datetime.datetime.now().strftime("%Y_%b_%d_%H_%M_%S_%f")))
    with open(TRAIN_DIRECTORY / "checkpoints" / "optimizer.json", mode="w", encoding="utf-8") as f:
        f.write(json.dumps(serialize(optimizer)))
    model.save(str(TRAIN_DIRECTORY / "checkpoints" / datetime.datetime.now().strftime("%Y_%b_%d_%H_%M_%S_%f"))) # Saving one more
    # model.summary()
    # plot_model(model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)
