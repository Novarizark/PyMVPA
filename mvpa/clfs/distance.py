#emacs: -*- mode: python-mode; py-indent-offset: 4; indent-tabs-mode: nil -*-
#ex: set sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the PyMVPA package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Distance functions to be used in kernels and elsewhere
"""

__docformat__ = 'restructuredtext'

import numpy as N
from mvpa.base import externals

if __debug__:
    from mvpa.base import debug, warning


def cartesianDistance(a, b):
    """Return Cartesian distance between a and b
    """
    return N.linalg.norm(a-b)


def absminDistance(a, b):
    """Returns dinstance max(\|a-b\|)
    XXX There must be better name!

    Useful to select a whole cube of a given "radius"
    """
    return max(abs(a-b))


def manhattenDistance(a, b):
    """Return Manhatten distance between a and b
    """
    return sum(abs(a-b))


def mahalanobisDistance(x, y=None, w=None):
    """Caclulcate Mahalanobis distance of the pairs of points.

    :Parameters:
      `x`
        first list of points. Rows are samples, columns are
        features.
      `y`
        second list of points (optional)
      `w` : N.ndarray
        optional inverse covariance matrix between the points. It is
        computed if not given

    Inverse covariance matrix can be calculated with the following

      w = N.linalg.solve(N.cov(x.T), N.identity(x.shape[1]))

    or

      w = N.linalg.inv(N.cov(x.T))
    """
    # see if pairwise between two matrices or just within a single matrix
    if y is None:
        # pairwise distances of single matrix
        # calculate the inverse correlation matrix if necessary
        if w is None:
            w = N.linalg.inv(N.cov(x.T))

        # get some shapes of the data
        mx, nx = x.shape
        #mw, nw = w.shape

        # allocate for the matrix to fill
        d = N.zeros((mx, mx), dtype=N.float32)
        for i in range(mx-1):
            # get the current row to compare
            xi = x[i, :]
            # replicate the row
            xi = xi[N.newaxis, :].repeat(mx-i-1, axis=0)
            # take the distance between all the matrices
            dc = x[i+1:mx, :] - xi
            # scale the distance by the correlation
            d[i+1:mx, i] = N.real(N.sum((N.inner(dc, w) * N.conj(dc)), 1))
            # fill the other direction of the matrix
            d[i, i+1:mx] = d[i+1:mx, i].T
    else:
        # is between two matrixes
        # calculate the inverse correlation matrix if necessary
        if w is None:
            # calculate over all points
            w = N.linalg.inv(N.cov(N.concatenate((x, y)).T))

        # get some shapes of the data
        mx, nx = x.shape
        my, ny = y.shape

        # allocate for the matrix to fill
        d = N.zeros((mx, my), dtype=N.float32)

        # loop over shorter of two dimensions
        if mx <= my:
            # loop over the x patterns
            for i in range(mx):
                # get the current row to compare
                xi = x[i, :]
                # replicate the row
                xi = xi[N.newaxis, :].repeat(my, axis=0)
                # take the distance between all the matrices
                dc = xi - y
                # scale the distance by the correlation
                d[i, :] = N.real(N.sum((N.inner(dc, w) * N.conj(dc)), 1))
        else:
            # loop over the y patterns
            for j in range(my):
                # get the current row to compare
                yj = y[j, :]
                # replicate the row
                yj = yj[N.newaxis, :].repeat(mx, axis=0)
                # take the distance between all the matrices
                dc = x - yj
                # scale the distance by the correlation
                d[:, j] = N.real(N.sum((N.inner(dc, w) * N.conj(dc)), 1))

    # return the dist
    return N.sqrt(d)


def squared_euclidean_distance(data1, data2=None, weight=None):
    """Compute weighted euclidean distance matrix between two datasets.


    :Parameters:
      data1 : N.ndarray
          first dataset
      data2 : N.ndarray
          second dataset. If None, compute the euclidean distance between
          the first dataset versus itself.
          (Defaults to None)
      weight : N.ndarray
          vector of weights, each one associated to each dimension of the
          dataset (Defaults to None)
    """
    if __debug__:
        # check if both datasets are floating point
        if not N.issubdtype(data1.dtype, 'f') \
           or (data2 is not None and not N.issubdtype(data2.dtype, 'f')):
            warning('Computing euclidean distance on integer data ' \
                    'is not supported.')

    # removed for efficiency (see below)
    #if weight is None:
    #    weight = N.ones(data1.shape[1], 'd') # unitary weight

    # In the following you can find faster implementations of this
    # basic code:
    #
    # squared_euclidean_distance_matrix = \
    #           N.zeros((data1.shape[0], data2.shape[0]), 'd')
    # for i in range(size1):
    #     for j in range(size2):
    #         squared_euclidean_distance_matrix[i, j] = \
    #           ((data1[i, :]-data2[j, :])**2*weight).sum()
    #         pass
    #     pass

    # Fast computation of distance matrix in Python+NumPy,
    # adapted from Bill Baxter's post on [numpy-discussion].
    # Basically: (x-y)**2*w = x*w*x - 2*x*w*y + y*y*w

    # based on value of weight and data2 we might save on computation
    # and resources
    if weight is None:
        data1w = data1
        if data2 is None:
            data2, data2w = data1, data1w
        else:
            data2w = data2
    else:
        data1w = data1 * weight
        if data2 is None:
            data2, data2w = data1, data1w
        else:
            data2w = data2 * weight

    squared_euclidean_distance_matrix = \
        (data1w * data1).sum(1)[:, None] \
        -2 * N.dot(data1w, data2.T) \
        + (data2 * data2w).sum(1)

    # correction to some possible numerical instabilities:
    less0 = squared_euclidean_distance_matrix < 0
    if __debug__ and 'CHECK_STABILITY' in debug.active:
        less0num = N.sum(less0)
        if less0num > 0:
            norm0 = N.linalg.norm(squared_euclidean_distance_matrix[less0])
            totalnorm = N.linalg.norm(squared_euclidean_distance_matrix)
            if totalnorm != 0 and norm0 / totalnorm > 1e-8:
                warning("Found %d elements out of %d unstable (<0) in " \
                        "computation of squared_euclidean_distance_matrix. " \
                        "Their norm is %s when total norm is %s" % \
                        (less0num, N.sum(less0.shape), norm0, totalnorm))
    squared_euclidean_distance_matrix[less0] = 0
    return squared_euclidean_distance_matrix


def correlation(X, Y):
    """Return correlations matrix between the rows of two matrizes X and Y.

    This functions computes a matrix of correlations between all pairs of
    rows of two matrizes. Unlike NumPy's corrcoef() this function will only
    considers pairs across matrizes and not within, e.g. both elements of
    a pair never have the same source matrix as origin.

    Both arrays need to have the same number of columns.

    :Parameters:
      X: 2D-array
      Y: 2D-array

    Example:

      >>> X = N.random.rand(20,80)
      >>> Y = N.random.rand(5,80)
      >>> C = correlation(X, Y)
      >>> print C.shape
      (20, 5)
    """
    # check if matrizes have same number of columns
    if __debug__:
        if not X.shape[1] == Y.shape[1]:
            raise ValueError, 'correlation() requires to matrizes with the ' \
                              'same #columns (Got: %s and %s)' \
                              % (X.shape, Y.shape)

    # zscore each sample/row
    Zx = X - N.c_[X.mean(axis=1)]
    Zx /= N.c_[X.std(axis=1)]
    Zy = Y - N.c_[Y.mean(axis=1)]
    Zy /= N.c_[Y.std(axis=1)]

    return (N.matrix(Zx) * N.matrix(Zy).T) / Zx.shape[1]


def pnorm_w_python(data1, data2=None, weight=None, p=2,
                   heuristic='auto', use_sq_euclidean=True):
    """Weighted p-norm between two datasets (pure Python implementation)

    ||x - x'||_w = (\sum_{i=1...N} (w_i*|x_i - x'_i|)**p)**(1/p)

    :Parameters:
      data1 : N.ndarray
        First dataset
      data2 : N.ndarray or None
        Optional second dataset
      weight : N.ndarray or None
        Optional weights per 2nd dimension (features)
      p
        Power
      heuristic : basestring
        Which heuristic to use:
         * 'samples' -- python sweep over 0th dim
         * 'features' -- python sweep over 1st dim
         * 'auto' decides automatically. If # of features (shape[1]) is much
           larger than # of samples (shape[0]) -- use 'samples', and use
           'features' otherwise
      use_sq_euclidean : bool
        Either to use squared_euclidean_distance_matrix for computation if p==2
    """
    if weight == None:
        weight = N.ones(data1.shape[1], 'd')
        pass

    if p == 2 and use_sq_euclidean:
        return N.sqrt(squared_euclidean_distance(data1=data1, data2=data2,
                                                 weight=weight**2))

    if data2 == None:
        data2 = data1
        pass

    S1,F1 = data1.shape[:2]
    S2,F2 = data2.shape[:2]
    # sanity check
    if not (F1==F2==weight.size):
        raise ValueError, \
              "Datasets should have same #columns == #weights. Got " \
              "%d %d %d" % (F1, F2, weight.size)
    d = N.zeros((S1, S2), 'd')

    # Adjust local functions for specific p values
    # pf - power function
    # af - after function
    if p == 1:
        pf = lambda x:x
        af = lambda x:x
    else:
        pf = lambda x:x ** p
        af = lambda x:x ** (1.0/p)

    # heuristic 'auto' might need to be adjusted
    if heuristic == 'auto':
        heuristic = {False: 'samples',
                     True: 'features'}[(F1/S1) < 500]

    if heuristic == 'features':
        #  Efficient implementation if the feature size is little.
        for NF in range(F1):
            d += pf(N.abs(N.subtract.outer(data1[:,NF],
                                           data2[:,NF]))*weight[NF])
            pass
    elif heuristic == 'samples':
        #  Efficient implementation if the feature size is much larger
        #  than number of samples
        for NS in xrange(S1):
            dfw = pf(N.abs(data1[NS] - data2) * weight)
            d[NS] = N.sum(dfw, axis=1)
            pass
    else:
        raise ValueError, "Unknown heuristic '%s'. Need one of " \
              "'auto', 'samples', 'features'" % heuristic
    return af(d)


if externals.exists('weave'):
    from scipy import weave
    from scipy.weave import converters

    def pnorm_w(data1, data2=None, weight=None, p=2):
        """Weighted p-norm between two datasets (scipy.weave implementation)

        ||x - x'||_w = (\sum_{i=1...N} (w_i*|x_i - x'_i|)**p)**(1/p)

        :Parameters:
          data1 : N.ndarray
            First dataset
          data2 : N.ndarray or None
            Optional second dataset
          weight : N.ndarray or None
            Optional weights per 2nd dimension (features)
          p
            Power
        """

        if weight == None:
            weight = N.ones(data1.shape[1], 'd')
            pass
        S1, F1 = data1.shape[:2]
        code = ""
        if data2 == None or id(data1)==id(data2):
            if not (F1==weight.size):
                raise ValueError, \
                      "Dataset should have same #columns == #weights. Got " \
                      "%d %d" % (F1, weight.size)
            F = F1
            d = N.zeros((S1, S1), 'd')
            try:
                code_peritem = \
                    {1.0 : "tmp = tmp+weight(t)*fabs(data1(i,t)-data1(j,t))",
                     2.0 : "tmp2 = weight(t)*(data1(i,t)-data1(j,t));" \
                     " tmp = tmp + tmp2*tmp2"}[p]
            except KeyError:
                code_peritem = "tmp = tmp+pow(weight(t)*fabs(data1(i,t)-data1(j,t)),p)"

            code = """
            int i,j,t;
            double tmp, tmp2;
            for (i=0; i<S1-1; i++) {
                for (j=i+1; j<S1; j++) {
                    tmp = 0.0;
                    for(t=0; t<F; t++) {
                        %s;
                        }
                    d(i,j) = tmp;
                    }
                }
            return_val = 0;
            """ % code_peritem


            counter = weave.inline(code,
                               ['data1', 'S1', 'F', 'weight', 'd', 'p'],
                               type_converters=converters.blitz,
                               compiler = 'gcc')
            d = d + N.triu(d).T # copy upper part to lower part
            return d**(1.0/p)

        S2,F2 = data2.shape[:2]
        if not (F1==F2==weight.size):
            raise ValueError, \
                  "Datasets should have same #columns == #weights. Got " \
                  "%d %d %d" % (F1, F2, weight.size)
        F = F1
        d = N.zeros((S1, S2), 'd')
        try:
            code_peritem = \
                {1.0 : "tmp = tmp+weight(t)*fabs(data1(i,t)-data2(j,t))",
                 2.0 : "tmp2 = weight(t)*(data1(i,t)-data2(j,t));" \
                 " tmp = tmp + tmp2*tmp2"}[p]
        except KeyError:
            code_peritem = "tmp = tmp+pow(weight(t)*fabs(data1(i,t)-data2(j,t)),p)"
            pass

        code = """
        int i,j,t;
        double tmp, tmp2;
        for (i=0; i<S1; i++) {
            for (j=0; j<S2; j++) {
                tmp = 0.0;
                for(t=0; t<F; t++) {
                    %s;
                    }
                d(i,j) = tmp;
                }
            }
        return_val = 0;

        """ % code_peritem

        counter = weave.inline(code,
                               ['data1', 'data2', 'S1', 'S2',
                                'F', 'weight', 'd', 'p'],
                               type_converters=converters.blitz,
                               compiler = 'gcc')
        return d**(1.0/p)

else:
    # Bind pure python implementation
    pnorm_w = pnorm_w_python
    pass

