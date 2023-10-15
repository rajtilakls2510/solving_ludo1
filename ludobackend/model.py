import tensorflow as tf
from tensorflow.keras.layers import Conv1D, BatchNormalization, Dense, Activation, Add, Dense, Input, Flatten
from tensorflow.keras.models import Model
# from keras.utils.vis_utils import plot_model


# The following code is written exactly with reference to AlphaZero Paper
# No changes are made as of now

# We can change parameters and other stuff if needed

def residual_block(x, filters, kernel_size = 3):
    x1 = Conv1D(filters, kernel_size, padding = 'same')(x)
    x1 = BatchNormalization()(x1)
    x1 = Activation('relu')(x1)

    x2 = Conv1D(filters, kernel_size, padding = 'same')(x1)
    x2 = BatchNormalization()(x2)

    x = Add()([x, x2])
    x = Activation('relu')(x)

    return x

def value_head(x):
    x = Conv1D(1, 1, padding = 'same')(x)
    x = BatchNormalization()(x)
    x = Activation('relu')(x)

    x = Flatten()(x)
    x = Dense(128, activation = 'relu')(x)
    x = Dense(1, activation ='tanh')(x)

    return x

def nn_model(input_shape):
    input_layer = Input(shape = input_shape)

    x = Conv1D(128, 3, padding = 'same')(input_layer)
    x = BatchNormalization()(x)
    x = Activation('relu')(x)

    for _ in range(28):
        x = residual_block(x, 128)

    value_output = value_head(x)

    model = Model(inputs = input_layer, outputs = value_output)

    return model


# if __name__ == "__main__":
#     input_shape = (59,21)
#     model = nn_model(input_shape)

#     model.summary()
    # plot_model(model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)
