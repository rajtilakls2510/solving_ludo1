import json
import datetime
import os
import argparse
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import tensorflow as tf
from tensorflow.keras.layers import Conv1D, BatchNormalization, Dense, Activation, Add, Dense, Input, Flatten
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam, schedules, serialize
# tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)
from pathlib import Path


# The following code is written exactly with reference to AlphaZero Paper
# No changes are made as of now

# We can change parameters and other stuff if needed

def residual_block(x, filters, kernel_size=3):
    x1 = Conv1D(filters, kernel_size, padding='same', kernel_regularizer=tf.keras.regularizers.L2(1e-4),
                bias_regularizer=tf.keras.regularizers.L2(1e-4))(x)
    x1 = BatchNormalization()(x1)
    x1 = Activation('relu')(x1)

    x2 = Conv1D(filters, kernel_size, padding='same', kernel_regularizer=tf.keras.regularizers.L2(1e-4),
                bias_regularizer=tf.keras.regularizers.L2(1e-4))(x1)
    x2 = BatchNormalization()(x2)

    x = Add()([x, x2])
    x = Activation('relu')(x)

    return x


def value_head(x):
    x = Conv1D(1, 1, padding='same', kernel_regularizer=tf.keras.regularizers.L2(1e-4),
               bias_regularizer=tf.keras.regularizers.L2(1e-4))(x)
    x = BatchNormalization()(x)
    x = Activation('relu')(x)

    x = Flatten()(x)
    x = Dense(256, activation='relu', kernel_regularizer=tf.keras.regularizers.L2(1e-4),
              bias_regularizer=tf.keras.regularizers.L2(1e-4))(x)
    x = Dense(1, activation='tanh', kernel_regularizer=tf.keras.regularizers.L2(1e-4),
              bias_regularizer=tf.keras.regularizers.L2(1e-4))(x)

    return x


def nn_model(input_shape):
    input_layer = Input(shape=input_shape)

    x = Conv1D(256, 3, padding='same', kernel_regularizer=tf.keras.regularizers.L2(1e-4),
               bias_regularizer=tf.keras.regularizers.L2(1e-4))(input_layer)
    x = BatchNormalization()(x)
    x = Activation('relu')(x)

    for _ in range(40):
        x = residual_block(x, 256)

    value_output = value_head(x)

    model = Model(inputs=input_layer, outputs=value_output)

    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path", type=str, default="train_config.json",
                        help="The config file that defines the configuration of the training run")
    args = parser.parse_args()
    config_file = args.config_path

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.loads(f.read())

    root_path = Path(config["root_path"])
    os.makedirs(root_path, exist_ok=True)
    lr = config["learner"]["lr_schedule"]
    dummy_schedule = schedules.PiecewiseConstantDecay(boundaries=lr["boundaries"], values=lr["lrs"])
    optimizer = Adam(learning_rate=dummy_schedule)
    input_shape = (59, 25)
    model = nn_model(input_shape)
    model.compile(optimizer=optimizer, loss=tf.keras.losses.MeanSquaredError())
    os.makedirs(root_path / config["checkpoints_subpath"], exist_ok=True)
    os.makedirs(root_path / config["experience_store_subpath"], exist_ok=True)
    os.makedirs(root_path / config["log_store_subpath"], exist_ok=True)

    current_checkpoint = datetime.datetime.now().strftime('%Y_%b_%d_%H_%M_%S_%f')
    model.save(
        str(root_path / config["checkpoints_subpath"] / current_checkpoint))
    config["actor"]["checkpoints"] = [current_checkpoint]
    config["actor"]["best_checkpoint_indices"] = [0]
    config["evaluator"]["newest_checkpoint"] = current_checkpoint
    config["evaluator"]["evaluated"] = True

    with open(config_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(config))

    print(model.summary())
    print(f"Found config file with root path: {config['root_path']}")
