import tensorflow as tf
from pathlib import Path
from tensorflow.keras.optimizers import schedules
tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)
from initializer import nn_model
loss = tf.keras.losses.MeanSquaredError()
# d = Path("runs") / "run1" / "checkpoints" / "2023_Oct_21_12_18_00_783716"
model = nn_model(input_shape=(59,21))


model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=schedules.PiecewiseConstantDecay(boundaries=[0,1,], values=[1e-2, 1e-3, 1e-4])))
print("OPt0: ",model.optimizer.learning_rate(model.optimizer.iterations))
x_batch = tf.zeros(shape=(2,59,21))
y_batch = tf.zeros(shape=(2,1))
with tf.GradientTape() as tape:
    tape.watch(x_batch)
    y_pred = model(x_batch)
    l = loss(y_pred, y_batch)
grads = tape.gradient(l, model.trainable_variables)
model.optimizer.apply_gradients(zip(grads, model.trainable_variables))

model.save("model")

print("OPt1: ", model.optimizer.learning_rate(model.optimizer.iterations))
model2 = tf.keras.models.load_model("model")
model2.optimizer.iterations = tf.Variable(0, dtype=tf.float32)
# model2.optimizer.learning_rate = schedules.PiecewiseConstantDecay(boundaries=[1,2,], values=[1e-2, 1e-3, 1e-4])
#
x_batch = tf.zeros(shape=(2,59,21))
y_batch = tf.zeros(shape=(2,1))
with tf.GradientTape() as tape:
    tape.watch(x_batch)
    y_pred = model2(x_batch)
    l = loss(y_pred, y_batch)
grads = tape.gradient(l, model2.trainable_variables)
model2.optimizer.apply_gradients(zip(grads, model2.trainable_variables))
print("OPt2: ",model2.optimizer.iterations, model2.optimizer.learning_rate(model2.optimizer.iterations))
x_batch = tf.zeros(shape=(2,59,21))
y_batch = tf.zeros(shape=(2,1))
with tf.GradientTape() as tape:
    tape.watch(x_batch)
    y_pred = model2(x_batch)
    l = loss(y_pred, y_batch)
grads = tape.gradient(l, model2.trainable_variables)
model2.optimizer.apply_gradients(zip(grads, model2.trainable_variables))
print("OPt3: ",model2.optimizer.iterations, model2.optimizer.learning_rate(model2.optimizer.iterations))
