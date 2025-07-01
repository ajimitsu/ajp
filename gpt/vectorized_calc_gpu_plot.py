import numpy as np
import matplotlib.pyplot as plt

# Try CuPy for GPU acceleration if available
# Google Colab
try:
    import cupy as cp
    xp = cp  # Use CuPy on GPU
    print("✅ Using GPU via CuPy.")
except ImportError:
    xp = np  # Fallback to NumPy on CPU
    print("⚠️ CuPy not available. Falling back to CPU with NumPy.")

def vectorized_calculation(x, y):
    """
    Perform a vectorized calculation on 2D input arrays x and y.

    Formula:
        z = sin(x) + log(y + 1) * sqrt(x^2 + y^2)

    Args:
        x (ndarray): Matrix of input values.
        y (ndarray): Matrix of input values.

    Returns:
        ndarray: Computed matrix (on GPU or CPU).
    """
    z = xp.sin(x) + xp.log(y + 1) * xp.sqrt(x**2 + y**2)
    return z

def main():
    # Create a 2D meshgrid
    x_vals = xp.linspace(0, 10, 500)
    y_vals = xp.linspace(0, 5, 500)
    X, Y = xp.meshgrid(x_vals, y_vals)

    # Compute
    Z = vectorized_calculation(X, Y)

    # Move result to CPU for plotting if on GPU
    if xp is not np:
        Z = cp.asnumpy(Z)
        X = cp.asnumpy(X)
        Y = cp.asnumpy(Y)

    # Plotting
    plt.figure(figsize=(8, 6))
    plt.contourf(X, Y, Z, levels=50, cmap='viridis')
    plt.colorbar(label='z value')
    plt.title("Vectorized Calculation with sin + log * sqrt")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
