/**
 * @file   weighted_average_wirelength_cuda_merged_kernel.cu
 * @author Yibo Lin
 * @date   Sep 2019
 */

#include <cfloat>
#include <stdio.h>
#include "assert.h"
#include "cuda_runtime.h"
#include "utility/src/utils.cuh"

DREAMPLACE_BEGIN_NAMESPACE

template <typename T>
__global__ void computeWeightedAverageWirelength(
    const T *x, const T *y,
    const int *flat_netpin,
    const int *netpin_start,
    const unsigned char *net_mask,
    int num_nets,
    const T *inv_gamma,
    // 0 -> inv_gamma is a single scalar shared by all nets (default, bit-identical
    // to the original kernel); 1 -> inv_gamma is a per-net array indexed by net id
    int gamma_stride,
    T *partial_wl,
    T *grad_intermediate_x, T *grad_intermediate_y)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    int ii = i >> 1;
    if (ii < num_nets && net_mask[ii])
    {
        const T *values;
        T *grads;
        if (i & 1)
        {
            values = y;
            grads = grad_intermediate_y;
        }
        else
        {
            values = x;
            grads = grad_intermediate_x;
        }

        const T ig = inv_gamma[ii * gamma_stride];

        // int degree = netpin_start[ii+1]-netpin_start[ii];
        T x_max = -FLT_MAX;
        T x_min = FLT_MAX;
        for (int j = netpin_start[ii]; j < netpin_start[ii + 1]; ++j)
        {
            T xx = values[flat_netpin[j]];
            x_max = max(xx, x_max);
            x_min = min(xx, x_min);
        }

        T xexp_x_sum = 0;
        T xexp_nx_sum = 0;
        T exp_x_sum = 0;
        T exp_nx_sum = 0;
        for (int j = netpin_start[ii]; j < netpin_start[ii + 1]; ++j)
        {
            T xx = values[flat_netpin[j]];
            T exp_x = exp((xx - x_max) * ig);
            T exp_nx = exp((x_min - xx) * ig);

            xexp_x_sum += xx * exp_x;
            xexp_nx_sum += xx * exp_nx;
            exp_x_sum += exp_x;
            exp_nx_sum += exp_nx;
        }

        partial_wl[i] = xexp_x_sum / exp_x_sum - xexp_nx_sum / exp_nx_sum;

        T b_x = ig / (exp_x_sum);
        T a_x = (1.0 - b_x * xexp_x_sum) / exp_x_sum;
        T b_nx = -ig / (exp_nx_sum);
        T a_nx = (1.0 - b_nx * xexp_nx_sum) / exp_nx_sum;

        for (int j = netpin_start[ii]; j < netpin_start[ii + 1]; ++j)
        {
            T xx = values[flat_netpin[j]];
            T exp_x = exp((xx - x_max) * ig);
            T exp_nx = exp((x_min - xx) * ig);

            grads[flat_netpin[j]] = (a_x + b_x * xx) * exp_x - (a_nx + b_nx * xx) * exp_nx;
        }
    }
}

template <typename T>
int computeWeightedAverageWirelengthCudaMergedLauncher(
    const T *x, const T *y,
    const int *flat_netpin,
    const int *netpin_start,
    const unsigned char *net_mask,
    int num_nets,
    const T *inv_gamma,
    int gamma_stride,
    T *partial_wl,
    T *grad_intermediate_x, T *grad_intermediate_y)
{
    int thread_count = 64;
    int block_count = (num_nets * 2 + thread_count - 1) / thread_count; // separate x and y

    computeWeightedAverageWirelength<<<block_count, thread_count>>>(
        x, y,
        flat_netpin,
        netpin_start,
        net_mask,
        num_nets,
        inv_gamma,
        gamma_stride,
        partial_wl,
        grad_intermediate_x, grad_intermediate_y);

    return 0;
}

#define REGISTER_KERNEL_LAUNCHER(T)                                    \
    template int computeWeightedAverageWirelengthCudaMergedLauncher<T>( \
        const T *x, const T *y,                                        \
        const int *flat_netpin,                                        \
        const int *netpin_start,                                       \
        const unsigned char *net_mask,                                 \
        int num_nets,                                                  \
        const T *inv_gamma,                                            \
        int gamma_stride,                                              \
        T *partial_wl,                                                 \
        T *grad_intermediate_x, T *grad_intermediate_y);

REGISTER_KERNEL_LAUNCHER(float);
REGISTER_KERNEL_LAUNCHER(double);

DREAMPLACE_END_NAMESPACE
