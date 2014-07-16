""" Collection of classes for representing aerosol size distributions.

Most commonly, one would use the :class:`Lognorm` distribution. However,
for the sake of completeness, other canonical distributions will be
included here, with the notion that this package could be extended to
describe droplet size distributions or other collections of objects.

"""
from abc import ABCMeta, abstractmethod

import numpy as np
from scipy.special import erf

class BaseDistribution:
    """ Interface for distributions, to ensure that they contain a pdf method.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def pdf(self, x):
        """ Number density function. """

    @abstractmethod
    def __repr__(self):
        """ Representation function. """

class Lognorm(BaseDistribution):
    """ Lognormal size distribution.

    An instance of :class:`Lognorm` contains a construction of a lognormal distribution
    and the utilities necessary for computing statistical functions associated
    with that distribution. The parameters of the constructor are invariant with respect
    to what length and concentration unit you choose; that is, if you use meters for
    ``mu`` and cm**-3 for ``N``, then you should keep these in mind when evaluating
    the :func:`pdf` and :func:`cdf` functions and when interpreting moments.

    Parameters
    ----------
    mu : float
        Median/geometric mean radius, length unit.
    sigma : float
        Geometric standard deviation, unitless.
    N : float, optional (default=1.0)
        Total number concentration, concentration unit.
    base : {'e', 10.0} (default='e')
        Base of logarithm in lognormal distribution.

    Attributes
    ----------
    median, mean : float
        Pre-computed statistical quantities

    Methods
    -------
    pdf(x)
        Evaluate distribution at a particular value
    cdf(x)
        Evaluate cumulative distribution at a particular value.
    moment(k)
        Compute the *k*-th moment of the lognormal distribution.

    """

    def __init__(self, mu, sigma, N=1.0, base="e"):
        self.mu = mu
        self.sigma = sigma
        self.N = N

        self.base = base
        if self.base in ["e", np.e]:
            self.log = np.log
        elif self.base == 10.:
            self.log = np.log10
        else:
            self.log_base = np.log(self.base)
            self.log = lambda x: np.log(x)/self.log_base

        # Compute moments
        self.median = self.mu
        self.mean = self.mu*np.exp(0.5*self.sigma**2)

    def cdf(self, x):
        """ Cumulative density function

        .. math::
            \\text{CDF} = \\frac{N}{2}\\left(1.0 + \\text{erf}(\\frac{\log{x/\mu}}{\sqrt{2}\log{\sigma}}) \\right)

        """
        erf_arg = (self.log(x/self.mu))/(np.sqrt(2.0)*self.log(self.sigma))
        return (self.N/2.0)*(1.0+erf(erf_arg))

    def pdf(self, x):
        """ Probability density function

        .. math::
            \\text{PDF} = \\frac{N}{\sqrt{2\pi}\log\sigma x}\exp\\left( -\\frac{\log{x/\mu}^2}{2\log^2\sigma} \\right)

        """
        scaling = self.N/(np.sqrt(2.0*np.pi)*self.log(self.sigma))
        exponent = ((self.log(x/self.mu))**2)/(2.0*(self.log(self.sigma))**2)
        return (scaling/x)*np.exp(-exponent)

    def moment(self, k):
        """ Compute the k-th moment of the lognormal distribution

        .. math::
            F(k) = N\mu^k\exp\\left( \\frac{k^2}{2} \ln^2 \sigma \\right)

        """
        scaling = (self.mu**k)*self.N
        exponent = (((k**2)/2.)*(self.log(self.sigma))**2)
        return scaling*self.N*np.exp(exponent)

    def stats(self):
        """ Compute useful statistics for a lognormal distribution

        Returns
        -------
        dict
            Dictionary containing the stats ``mean_radius``, ``total_diameter``,
            ``total_surface_area``, ``total_volume``, ``mean_surface_area``,
            ``mean_volume``, and ``effective_radius``

        """
        stats_dict = dict()
        stats_dict['mean_radius'] = self.mu*np.exp(0.5*self.sigma**2)

        stats_dict['total_diameter'] = self.N*stats_dict['mean_radius']
        stats_dict['total_surface_area'] = 4.*np.pi*self.moment(2.0)
        stats_dict['total_volume'] = (4.*np.pi/3.)*self.moment(3.0)

        stats_dict['mean_surface_area'] = stats_dict['total_surface_area']/self.N
        stats_dict['mean_volume'] = stats_dict['total_volume']/self.N

        stats_dict['effective_radius'] = stats_dict['total_volume']/ \
                                         stats_dict['total_surface_area']

        return stats_dict

    def __repr__(self):
        return "Lognorm| mu = %2.2e, sigma = %2.2e, Total = %2.2e |" % \
               (self.mu, self.sigma, self.N)

class MultiModeLognorm(BaseDistribution):
    """Multimode lognormal distribution class.

    Container for multiple Lognorm classes representing a full aerosol size
    distribution.
    """

    def __init__(self, mus, sigmas, Ns, base="e"):

        dist_params = zip(mus, sigmas, Ns)
        from operator import itemgetter
        dist_params = sorted(dist_params, key=itemgetter(0))

        self.mus, self.sigmas, self.Ns = zip(*dist_params)

        self.base = base

        self.lognorms = []
        for mu, sigma, N in zip(self.mus, self.sigmas, self.Ns):
            mode_dist = Lognorm(mu, sigma, N, base)
            self.lognorms.append(mode_dist)

    def cdf(self, x):
        return np.sum([d.cdf(x) for d in self.lognorms], axis=0)

    def pdf(self, x):
        return np.sum([d.pdf(x) for d in self.lognorms], axis=0)

    def __repr__(self):
        mus_str = "("+", ".join("%2.2e" % mu for mu in self.mus)+")"
        sigmas_str = "("+", ".join("%2.2e" % sigma for sigma in self.sigmas)+")"
        Ns_str = "("+", ".join("%2.2e" % N for N in self.Ns)+")"
        return "MultiModeLognorm| mus = %s, sigmas = %s, Totals = %s |" % \
               (mus_str, sigmas_str, Ns_str)

whitby_distributions = {
    # name: [nucleation, accumulation, coarse]
    #        mu = micron, N = cm**-3
    'marine': [Lognorm(0.01/2., 1.6, 340.), Lognorm(0.07/2., 2., 6.0),
               Lognorm(0.62/2., 2.7, 3.1)],
    'continental': [Lognorm(0.016/2., 1.6, 1000.), Lognorm(0.068/2., 2.1, 800.),
                    Lognorm(0.92/2., 2.2, 0.72)],
    'background': [Lognorm(0.01/2., 1.7, 6400.), Lognorm(0.076/2., 2., 2300.0),
                   Lognorm(1.02/2., 2.16, 3.2)],
    'urban': [Lognorm(0.014/2., 1.8, 10600.), Lognorm(0.054/2., 2.16, 32000.0),
              Lognorm(0.86/2., 2.21, 5.4)]
}

## Source = Aerosol-Cloud-Climate Interactions by Peter V. Hobbs, pg. 14
jaenicke_distributions = {
    "Polar": MultiModeLognorm(mus=(0.0689, 0.375, 4.29),
                              sigmas=(10**0.245, 10**0.300, 10**0.291),
                              Ns=(21.7, 0.186, 3.04e-4), base=10.),
    "Urban": MultiModeLognorm(mus=(0.00651, 0.00714, 0.0248),
                              sigmas=(10.**0.245, 10.**0.666, 10.**0.337),
                              Ns=(9.93e4, 1.11e3, 3.64e4), base=10.),
    "Background": MultiModeLognorm(mus=(0.0036, 0.127, 0.259),
                                   sigmas=(10.**0.645, 10.**0.253, 10.**0.425),
                                   Ns=(129., 59.7, 63.5), base=10.),
    "Maritime": MultiModeLognorm(mus=(0.0039, 0.133, 0.29),
                                 sigmas=(10.**0.657, 10.**0.210, 10.**0.396),
                                 Ns=(133., 66.6, 3.06), base=10.),
    "Remote Continental": MultiModeLognorm(mus=(0.01, 0.058, 0.9),
                                           sigmas=(10.**0.161, 10.**0.217, 10.**0.38),
                                           Ns=(3.2e3, 2.9e3, 0.3), base=10.),
    "Rural": MultiModeLognorm(mus=(0.00739, 0.0269, 0.0149),
                              sigmas=(10.**0.225, 10.**0.557, 10.**0.266),
                              Ns=(6.65e3, 147., 1990.), base=10.),
}