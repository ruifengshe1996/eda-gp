# Environment for DREAMPlace development. Usage: source env.sh
export GP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CUDA_HOME=$GP_ROOT/deps/cuda-11.8
export PATH=$GP_ROOT/deps/local/bin:$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$GP_ROOT/deps/local/lib:$CUDA_HOME/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export PKG_CONFIG_PATH=$GP_ROOT/deps/local/lib/pkgconfig:$GP_ROOT/deps/local/share/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}
source $GP_ROOT/venv/bin/activate
