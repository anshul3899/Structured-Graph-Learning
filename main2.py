import os
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from sklearn.datasets import make_sparse_spd_matrix
from sgl import LearnGraphTopolgy
from metrics import ModelSelection, Metrics
from utils import Operators
from scipy.linalg import block_diag

def generate_kcomponent_data(n, p, k_true):
    '''Makes k-component data and generate samples from GMRF
    
    Parameters
    ----------
    n_samples : int Number of samples 

    p : int Number of nodes per component

    k_true : int Number of components

    Returns
    -------
    X : data 2D ndarray (n_samples ⨉ n_features)

    cov_true : true covariance matrix  2D ndarray (n_features ⨉ n_features)

    prec_true : true precision matrix  2D ndarray (n_features ⨉ n_features)
    '''
    eps = 1e-4
    npk = int(p / k_true)
    a = int((npk*(npk-1))/2)
    # Assume each component fully connected
    w = np.ones(a)
    # uncomment to specify edge weights
    # w = np.random.rand(a,1)
    op = Operators()
    lw = op.L(w)
    # noise_graph = nx.fast_gnp_random_graph(p, 0.15, seed=4)
    # A_noise = np.asarray(nx.adjacency_matrix(noise_graph).todense())
    # A_noise = A_noise*0.4*np.random.rand(p, p)
    # A_noise = (A_noise + A_noise.T)/2
    # L_noise = np.diag(np.sum(A_noise, axis=1)) - A_noise
    L_true = block_diag(*[lw]*k_true)
    A_true = np.diag(np.diag(L_true)) - L_true
    # L_noisy = L_true + L_noise
    # A_noisy = A_true + A_noise
    cov_true = np.linalg.pinv(L_true)
    # cov_noisy = np.linalg.pinv(L_noisy)
    # normalization ??
    # d = np.sqrt(np.diag(cov_true))
    # cov_true /= d
    # cov_true /= d[:, np.newaxis]
    # prec_true *= d
    # prec_true *= d[:, np.newaxis]
    # sample from GMRF
    X = np.random.multivariate_normal(np.zeros(p), cov_true, size=n)
    # X -= X.mean(axis=0)
    # X /= X.std(axis=0)
    # plot laplacian
    fig = plt.figure(figsize=(15,15)) 
    plt.set_cmap('Reds')
    plt.title('True Laplacian')
    plt.imshow(L_true)
    plt.colorbar()
    filename = 'plots/kcomp_true_laplacian_ktrue=' + str(k_true) + '.png'
    fig.savefig(filename, format='png')

    # fig = plt.figure(figsize=(15,15)) 
    # plt.set_cmap('Reds')
    # plt.title('Noisy Laplacian')
    # plt.imshow(L_noisy)
    # plt.colorbar()
    # filename = 'plots/kcomp_noisy_laplacian_ktrue=' + str(k_true) + '.png'
    # fig.savefig(filename, format='png')
    # plot adjacency
    fig = plt.figure(figsize=(15,15)) 
    plt.title('True Adjacency')
    plt.imshow(A_true)
    plt.colorbar()
    filename = 'plots/kcomp_true_adj_ktrue=' + str(k_true) + '.png'
    fig.savefig(filename, format='png')

    # fig = plt.figure(figsize=(15,15)) 
    # plt.title('Noisy Adjacency')
    # plt.imshow(A_noisy)
    # plt.colorbar()
    # filename = 'plots/kcomp_noisy_adj_ktrue=' + str(k_true) + '.png'
    # fig.savefig(filename, format='png')
    return X, L_true, cov_true

def empirical_estimate(X, n_samples, plot=True):
    ''' Empirical estimation '''
    print('##########  Empirical Estimation  ##########')
    eps = 1e-4
    # Sample Covariance matrix
    cov_emp = np.dot(X.T, X) / n_samples
    prec_emp = np.linalg.pinv(cov_emp)
    A = np.diag(np.diag(prec_emp)) - prec_emp
    # uncomment to threshold in unweighted graph
    # A[A>eps] = 1
    A[A<eps] = 0
    # prec_emp = np.diag(np.sum(A, axis=1)) - A
    metric = Metrics(L_true, prec_emp)
    print('Rel error:', metric.relative_error())
    print('F1 score:', metric.f1_score())

    if plot:
        fig = plt.figure(figsize=(15,15)) 
        plt.title('Estimated Laplacian empirical k-comp')
        plt.imshow(prec_emp)
        plt.colorbar()
        filename = 'plots/kcomp_estimated_Laplacian_empirical.png'
        fig.savefig(filename, format='png')
        plt.close()

        fig = plt.figure(figsize=(15,15)) 
        plt.title('Estimated Adjacency empirical k-comp')
        plt.imshow(A)
        plt.colorbar()
        filename = 'plots/kcomp_estimated_adj_empirical.png'
        fig.savefig(filename, format='png')
        plt.close()
    return prec_emp, cov_emp


npk = 10
k_true = 4
p = npk*k_true
n = 30*p
np.random.seed(58)

plots_dir = './plots'
outs_dir = './outs'
if not os.path.exists(plots_dir):
    os.makedirs(plots_dir)
if not os.path.exists(outs_dir):
    os.makedirs(outs_dir)

X, L_true, cov_true = generate_kcomponent_data(n, p, k_true)
L_emp, cov_emp = empirical_estimate(X, n)
sgl = LearnGraphTopolgy(cov_emp, maxiter=3000, record_objective = True, record_weights = True)
# # check for k-component graph
print('##########  Assumed Graph structure: k-component graph  ##########')
K = 7
if K < 1:
    raise Exception('Increase k or number of components')
for k in range(1, K+1):
    print('===> k =', k)
    # estimate underlying graph
    graph = sgl.learn_k_component_graph(w0 = 'qp', k=k, beta=4)
    A_kcomp = graph['adjacency']
    eps = 1e-3
    thresh = np.mean(A_kcomp)
    A_kcomp[A_kcomp<thresh] = 0
    A_kcomp[A_kcomp>thresh] = 1
    L_kcomp = np.diag(np.sum(A_kcomp, axis=1)) - A_kcomp
    # L_kcomp = graph['laplacian']
    # plot laplacian
    fig = plt.figure(figsize=(15,15)) 
    plt.title('Estimated Laplacian k-comp')
    plt.imshow(L_kcomp)
    plt.colorbar()
    filename = 'plots/kcomp_estimated_Laplacian_k=' + str(k) + '.png'
    fig.savefig(filename, format='png')
    plt.close()
    # plot adjacency
    fig = plt.figure(figsize=(15,15)) 
    plt.title('Estimated Adjacency k-comp')
    plt.imshow(A_kcomp)
    plt.colorbar()
    filename = 'plots/kcomp_estimated_adj_k=' + str(k) + '.png'
    fig.savefig(filename, format='png')
    plt.close()

    mod_selection = ModelSelection()
    ebic = mod_selection.ebic(L_kcomp, cov_emp, n, p)
    metrics = Metrics(L_true, L_kcomp)
    print('train objective:', min(graph['obj_fun']), 'train NLL:', min(graph['nll']) )
    print('Rel error: {} F1 score: {}'.format(metrics.relative_error(), metrics.f1_score()))
    print('eBIC score:', ebic)

print('##########  Assumed Graph structure: connected bipartite graph  ##########')
graph = sgl.learn_bipartite_graph(z = 5, nu=1e4)
A_sga = graph['adjacency']
eps = 1e-3
A_sga[A_sga<eps] = 0
L_sga = graph['laplacian']
# plot laplacian
fig = plt.figure(figsize=(15,15)) 
plt.title('Estimated Laplacian Bipartite')
plt.imshow(L_sga)
plt.colorbar()
filename = 'plots/bipartite_estimated_Laplacian.png'
fig.savefig(filename, format='png')
plt.close()
# plot adjacency
fig = plt.figure(figsize=(15,15)) 
plt.title('Estimated Adjacency Bipartite')
plt.imshow(A_sga)
plt.colorbar()
filename = 'plots/bipartite_estimated_adj.png'
fig.savefig(filename, format='png')
plt.close()

mod_selection = ModelSelection()
ebic = mod_selection.ebic(L_sga, cov_emp, n, p)
metrics = Metrics(L_true, L_sga)
print('train objective:', min(graph['obj_fun']), 'train NLL:', min(graph['nll']) )
print('Rel error: {} F1 score: {}'.format(metrics.relative_error(), metrics.f1_score()))
print('eBIC score:', ebic)

# def SGL_EBIC(cov_emp, K = 7, plot=True):
#     ''' SGL + EBIC '''
#     eps = 1e-4
#     precs = []
#     adjs = []
#     ebics = []
#     m = ModelSelection()
#     sgl = LearnGraphTopolgy(cov_emp, maxiter=5000, record_objective = True, record_weights = True)
#     # check for k-component graph
#     print('##########  Assumed Graph structure: k-component graph  ##########')
#     if K < 1:
#         raise Exception('Increase k or number of components')
#     for k in range(1, K+1):
#         print('===> k =', k)
#         # estimate underlying graph
#         graph = sgl.learn_k_component_graph(k=k, beta=1e4)
#         L = graph['laplacian']
#         # thresholding
#         A = np.diag(np.diag(L)) - L
#         A[A>eps] = 1
#         A[A<eps] = 0
#         adjs.append(A)
#         L = np.diag(np.sum(A, axis=1)) - A
#         precs.append(L)
#         metric = Metrics(prec_true, L)
#         ebic = m.ebic(L, cov_emp, n_samples, n_features)
#         ebics.append(ebic)
#         print('train objective:', min(graph['obj_fun']), 'train NLL:', min(graph['nll']) )
#         print('Rel error: {} F1 score: {}'.format(metric.relative_error(), metric.f1_score()))
#         print('eBIC score:', ebic)

#     # check for bipartite graph
#     print('##########  Assumed Graph structure: connected bipartite graph  ##########')
#     graph = sgl.learn_bipartite_graph(z = 4, nu=1e4)
#     A = graph['adjacency']
#     A[A>eps] = 1
#     A[A<eps] = 0
#     adjs.append(A)
#     L = np.diag(np.sum(A, axis=1)) - A
#     precs.append(L)
#     metric = Metrics(prec_true, L)
#     ebic = m.ebic(L, cov_emp, n_samples, n_features)
#     ebics.append(ebic)
#     print('train objective:', min(graph['obj_fun']), 'train NLL:', min(graph['nll']) )
#     print('Rel error: {} F1 score: {}'.format(metric.relative_error(), metric.f1_score()))
#     print('eBIC score:', ebic)
#     # check for multi-component bipartite graph
#     print('##########  Assumed Graph structure: multi-component bipartite graph  ##########')


#     if plot:
#         # plot k-component graphs
#         for i in range(K):
#             fig = plt.figure(figsize=(15,15)) 
#             L = precs[i]
#             plt.title('Estimated Laplacian k=' + str(i+1))
#             plt.imshow(L)
#             plt.colorbar()
#             filename = 'plots/estimated_Laplacian_k=' + str(i+1) + '.png'
#             fig.savefig(filename, format='png')
#             plt.close()

#             fig = plt.figure(figsize=(15,15)) 
#             A = adjs[i]
#             plt.title('Estimated Adjacency k=' + str(i+1))
#             plt.imshow(A)
#             plt.colorbar()
#             filename = 'plots/estimated_adj_k=' + str(i+1) + '.png'
#             fig.savefig(filename, format='png')
#             plt.close()
#         # plot bipartite graph
#         fig = plt.figure(figsize=(15,15)) 
#         L = precs[K]
#         plt.title('Estimated Laplacian Bipartite')
#         plt.imshow(L)
#         plt.colorbar()
#         filename = 'plots/estimated_Laplacian_bipartite.png'
#         fig.savefig(filename, format='png')
#         plt.close()

#         fig = plt.figure(figsize=(15,15)) 
#         A = adjs[K]
#         plt.title('Estimated Adjacency Bipartite')
#         plt.imshow(A)
#         plt.colorbar()
#         filename = 'plots/estimated_adj_bipartite.png'
#         fig.savefig(filename, format='png')
#         plt.close()
#         # plot multi-component graphs

#     # save precision matrices and corresponding ebic scores
#     precs, ebics = np.asarray(precs), np.asarray(ebics)
#     with open('outs/outs.npy', 'wb') as f:
#         np.save(f, precs)
#         np.save(f, ebics)

# if __name__ == "__main__":
#     # actual graph k-component example
    # n_samples = 200
    # p = 10
    # k_true = 3
    # n_features = p*k_true
    # X, prec_true, cov_true = generate_kcomponent_data(n_samples, p, k_true)
    # prec_emp, cov_emp = empirical_estimate(X, n_samples)
#     SGL_EBIC(cov_emp, K=8)


    # with open('test.npy', 'rb') as f:
    #     precs = np.load(f)
    #     ebics = np.load(f)
    # k_ebic = ebics.index(max(ebics))
    # precs[k_ebic], np.linalg.pinv(precs[k_ebic]), k_ebic + 1