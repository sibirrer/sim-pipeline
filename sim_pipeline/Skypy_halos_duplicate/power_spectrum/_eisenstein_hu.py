"""Eisenstein and Hu.

This implements the Eisenstein and Hu fitting
formula for the matter power spectrum.
"""

from astropy.utils import isiterable
import numpy as np
from astropy import constants
from ._base import PowerSpectrum
from ._growth import growth_function_carroll
# TODO: This code has been temporarily borrowed from SkyPy.  Once the feature is available in the main branch or
#  release version of SkyPy,  this code should be deprecated and replaced with the official implementation. Original
#  Source: [https://github.com/skypyproject/skypy/tree/module/halos]

__all__ = [
    'EisensteinHu',
    'eisenstein_hu',
    'transfer_with_wiggles',
    'transfer_no_wiggles',
]


def transfer_with_wiggles(wavenumber, A_s, n_s, cosmology, kwmap=0.02):
    r''' Eisenstein & Hu transfer function with wiggles.
    This function returns the Eisenstein & Hu fitting formula for the transfer
    function with baryon acoustic oscillation wiggles. This is described in
    [1]_ and [2]_.

    Parameters
    ----------
    wavenumber : (nk,) array_like
        Array of wavenumbers in units of Mpc-1 at which to evaluate
        the linear matter power spectrum.
    cosmology : astropy.cosmology.Cosmology
        Cosmology object providing omega_matter, omega_baryon, Hubble parameter
        and CMB temperature at the present day.
    A_s, n_s: float
        Amplitude and spectral index of primordial scalar fluctuations.
    kwmap : float
        WMAP normalization for the amplitude of primordial scalar fluctuations,
        as described in [3]_, in units of Mpc-1.
        Default is 0.02.

    Returns
    -------
    transfer : (nk,) array_like
        Transfer function evaluated at the given array of wavenumbers for the
        input primordial power spectrum parameters A_s and n_s, cosmology and
        kwmap normalization.

    References
    ----------
    .. [1] Eisenstein D. J., Hu W., ApJ, 496, 605 (1998)
    .. [2] Eisenstein D. J., Hu W., ApJ, 511, 5 (1999)
    .. [3] Komatsu et al., ApJS, 180, 330 (2009)

    '''

    if isiterable(wavenumber):
        wavenumber = np.asarray(wavenumber)
    if np.any(wavenumber <= 0):
        raise ValueError('Wavenumbers must be positive')

    om0 = cosmology.Om0
    ob0 = cosmology.Ob0

    if not ob0:
        raise ValueError("Ob0 for input cosmology must be non-zero if "
                         "wiggles = True")

    h0 = cosmology.H0.value / 100
    Tcmb0 = cosmology.Tcmb0.value

    if not Tcmb0:
        raise ValueError("Tcmb0 for input cosmology must be non-zero if"
                         "wiggles = True")

    om0h2 = om0 * h0**2
    ob0h2 = ob0 * h0**2
    f_baryon = ob0 / om0

    # redshift and wavenumber equality
    k_eq = 7.46e-2 * om0h2 * (Tcmb0 / 2.7)**-2
    z_eq = 2.5e4 * om0h2 * (Tcmb0 / 2.7)**-4

    # sound horizon and k_silk
    z_drag_b1 = 0.313 * om0h2**-0.419 * (1 + 0.607 * om0h2**0.674)
    z_drag_b2 = 0.238 * om0h2**0.223
    z_drag = 1291 * om0h2**0.251 / (1 + 0.659 * om0h2**0.828) \
        * (1 + z_drag_b1 * ob0h2**z_drag_b2)

    r_drag = 31.5 * ob0h2 * (Tcmb0 / 2.7)**-4 * (1000. / z_drag)
    r_eq = 31.5 * ob0h2 * (Tcmb0 / 2.7)**-4 * (1000. / z_eq)

    sound_horizon = 2 / (3 * k_eq) * np.sqrt(6 / r_eq) * \
        np.log((np.sqrt(1 + r_drag) + np.sqrt(r_drag + r_eq)) /
               (1 + np.sqrt(r_eq)))
    k_silk = 1.6 * ob0h2**0.52 * om0h2**0.73 * (1 + (10.4 * om0h2)**-0.95)

    # alpha c
    alpha_c_a1 = (46.9 * om0h2)**0.670 * (1 + (32.1 * om0h2)**-0.532)
    alpha_c_a2 = (12.0 * om0h2)**0.424 * (1 + (45.0 * om0h2)**-0.582)
    alpha_c = alpha_c_a1 ** -f_baryon * alpha_c_a2 ** (-f_baryon**3)

    # beta_c
    beta_c_b1 = 0.944 / (1 + (458 * om0h2)**-0.708)
    beta_c_b2 = (0.395 * om0h2)**-0.0266
    beta_c = 1 / (1 + beta_c_b1 * ((1 - f_baryon)**beta_c_b2 - 1))

    y = (1.0 + z_eq) / (1 + z_drag)
    alpha_b_G = y * (-6 * np.sqrt(1 + y) + (2 + 3 * y)
                     * np.log((np.sqrt(1 + y) + 1) / (np.sqrt(1 + y) - 1)))
    alpha_b = 2.07 * k_eq * sound_horizon * (1 + r_drag)**-0.75 * alpha_b_G

    beta_node = 8.41 * om0h2 ** 0.435
    beta_b = 0.5 + f_baryon + (3 - 2 * f_baryon) * np.sqrt((17.2 * om0h2)**2
                                                           + 1.0)

    q = wavenumber / (13.41 * k_eq)
    ks = wavenumber * sound_horizon

    T_c_ln_beta = np.log(np.e + 1.8 * beta_c * q)
    T_c_ln_nobeta = np.log(np.e + 1.8 * q)
    T_c_C_alpha = 14.2 / alpha_c + 386. / (1 + 69.9 * q ** 1.08)
    T_c_C_noalpha = 14.2 + 386. / (1 + 69.9 * q ** 1.08)

    T_c_f = 1 / (1 + (ks / 5.4) ** 4)

    def f(a, b):
        return a / (a + b * q**2)

    T_c = T_c_f * f(T_c_ln_beta, T_c_C_noalpha) + \
        (1 - T_c_f) * f(T_c_ln_beta, T_c_C_alpha)

    s_tilde = sound_horizon * (1 + (beta_node / ks)**3)**(-1 / 3)
    ks_tilde = wavenumber * s_tilde

    T_b_T0 = f(T_c_ln_nobeta, T_c_C_noalpha)
    T_b_1 = T_b_T0 / (1 + (ks / 5.2)**2)
    T_b_2 = alpha_b / (1 + (beta_b / ks)**3) * np.exp(-(wavenumber/k_silk)**1.4)
    T_b = np.sinc(ks_tilde / np.pi) * (T_b_1 + T_b_2)

    transfer = f_baryon * T_b + (1 - f_baryon) * T_c

    return transfer


def transfer_no_wiggles(wavenumber, A_s, n_s, cosmology):
    r'''Eisenstein & Hu transfer function without wiggles.
    Eisenstein & Hu fitting formula for the transfer function without
    baryon acoustic oscillation wiggles. This is described in
    [1]_ and [2]_.

    Parameters
    ----------
    wavenumber : (nk,) array_like
        Array of wavenumbers in units of Mpc-1 at which to evaluate
        the linear matter power spectrum.
    A_s, n_s: float
        Amplitude and spectral index of primordial scalar fluctuations.
    cosmology : astropy.cosmology.Cosmology
        Cosmology object providing omega_matter, omega_baryon, Hubble parameter
        and CMB temperature in the present day.

    Returns
    -------
    transfer : (nk, ) array_like
        Transfer function evaluated at the given wavenumbers for the input
        primordial power spectrum parameters A_s and n_s, cosmology and kwmap
        normalization.

    References
    ----------
    .. [1] Eisenstein D. J., Hu W., ApJ, 496, 605 (1998)
    .. [2] Eisenstein D. J., Hu W., ApJ, 511, 5 (1999)
    .. [3] Komatsu et al., ApJS, 180, 330 (2009)

    '''

    if isiterable(wavenumber):
        wavenumber = np.asarray(wavenumber)
    if np.any(wavenumber <= 0):
        raise ValueError('Wavenumbers must be positive')

    om0 = cosmology.Om0
    ob0 = cosmology.Ob0
    h0 = cosmology.H0.value / 100
    Tcmb0 = cosmology.Tcmb0.value
    om0h2 = om0 * h0**2
    f_baryon = ob0 / om0

    alpha = 1 - 0.328 * np.log(431 * om0h2) * f_baryon + 0.38 * \
        np.log(22.3 * om0h2) * f_baryon**2
    sound = 44.5 * np.log(9.83 / om0h2) / \
        np.sqrt(1 + 10 * (f_baryon * om0h2)**(0.75))
    shape = om0h2 * (alpha + (1 - alpha) / (1 + (0.43 * wavenumber * sound)**4))
    aq = wavenumber * (Tcmb0 / 2.7)**2 / shape
    transfer = np.log(2 * np.e + 1.8 * aq) / \
        (np.log(2 * np.e + 1.8 * aq) +
         (14.2 + 731 / (1 + 62.5 * aq)) * aq * aq)

    return transfer


def eisenstein_hu(wavenumber, A_s, n_s, cosmology, kwmap=0.02, wiggle=True):
    """ Eisenstein & Hu matter power spectrum.
    This function returns the Eisenstein and Hu fitting function for the linear
    matter power spectrum with (or without) baryon acoustic oscillations, c.f.
    [1]_ and [2]_, using
    formulation from Komatsu et al (2009) in [3]_.

    Parameters
    ----------
    wavenumber : (nk, ) array_like
        Array of wavenumbers in units of Mpc-1 at which to evaluate
        the linear matter power spectrum.
    A_s, n_s: float
        Amplitude and spectral index of primordial scalar fluctuations.
    cosmology : astropy.cosmology.Cosmology
        Cosmology object providing omega_matter, omega_baryon, Hubble parameter
        and CMB temperature in the present day.
    kwmap : float
        WMAP normalization for the amplitude of primordial scalar fluctuations,
        as described in [3], in units of Mpc-1. Default is 0.02.
    wiggle : bool
        Boolean flag to set the use of baryion acoustic oscillations wiggles.
        Default is True, for which the power spectrum is computed with the
        wiggles.

    Returns
    -------
    power_spectrum : array_like
        Linear matter power spectrum in units of Mpc3,
        evaluated at the given wavenumbers for the input primordial
        power spectrum parameters
        A_s and n_s, cosmology, and kwmap normalization.

    References
    ----------
    .. [1] Eisenstein D. J., Hu W., ApJ, 496, 605 (1998)
    .. [2] Eisenstein D. J., Hu W., ApJ, 511, 5 (1999)
    .. [3] Komatsu et al., ApJS, 180, 330 (2009)

    """
    om0 = cosmology.Om0
    H0_c = (cosmology.H0 / constants.c).to_value('Mpc-1')

    if wiggle:
        transfer = transfer_with_wiggles(wavenumber, A_s, n_s, cosmology,
                                         kwmap)
    else:
        transfer = transfer_no_wiggles(wavenumber, A_s, n_s, cosmology)

    # Eq [74] in [3]
    power_spectrum = A_s * (2 * (wavenumber / H0_c)**2 / 5 / om0)**2 * \
        transfer**2 * (wavenumber / kwmap)**(n_s - 1) * 2 * \
        np.pi**2 / (wavenumber)**3

    return power_spectrum


class EisensteinHu(PowerSpectrum):
    """
    Power spectrum class using Eisenstein & Hu linear power spectrum described
    in [1]_ and [2]_, using formulation from Komatsu et al (2009) in [3]_.

    ...

    Attributes
    ----------
    A_s, n_s: float
        Amplitude and spectral index of primordial scalar fluctuations.
    cosmology : astropy.cosmology.Cosmology
        Cosmology object providing omega_matter, omega_baryon, Hubble parameter
        and CMB temperature in the present day.
    kwmap : float
        WMAP normalization for the amplitude of primordial scalar fluctuations,
        as described in [3], in units of Mpc-1. Default is 0.02.
    wiggle : bool
        Boolean flag to set the use of baryion acoustic oscillations wiggles.
        Default is True, for which the power spectrum is computed with the
        wiggles.

    References
    ----------
    .. [1] Eisenstein D. J., Hu W., ApJ, 496, 605 (1998)
    .. [2] Eisenstein D. J., Hu W., ApJ, 511, 5 (1999)
    .. [3] Komatsu et al., ApJS, 180, 330 (2009)
    """
    def __init__(self, A_s, n_s, cosmology, kwmap=0.02, wiggle=True):
        """
        Constructs all the necessary attributes for the EisensteinHu class.

        Parameters
        ----------
        A_s, n_s: float
            Amplitude and spectral index of primordial scalar fluctuations.
        cosmology : astropy.cosmology.Cosmology
            Cosmology object providing omega_matter, omega_baryon, Hubble
            parameter and CMB temperature in the present day.
        kwmap : float
            WMAP normalization for the amplitude of primordial scalar
            fluctuations, described in [3], in units of Mpc-1. Default is 0.02.
        wiggle : bool
            Boolean flag to set the use of baryion acoustic oscillation wiggles.
            Default is True, for which the power spectrum is computed with the
            wiggles.
        """
        self.A_s = A_s
        self.n_s = n_s
        self.cosmology = cosmology
        self.kwmap = kwmap
        self.wiggle = wiggle

    def __call__(self, wavenumber, redshift):
        """
        Calls the Eisenstein and Hu linear matter power spectrum.

        Parameters
        ----------
        wavenumber : (nk, ) array_like
            Array of wavenumbers in units of Mpc-1 at which to evaluate
            the linear matter power spectrum.
        redshift : (nz, ) array_like
            Array of redshifts at which to evaluate the linear matter power
            spectrum

        Returns
        -------
        pzk : array_like
            Linear matter power spectrum in units of Mpc3,
            evaluated at the given wavenumbers from the defined EisensteinHu
            object.
        """
        growth_function = growth_function_carroll(np.atleast_1d(redshift),
                                                  self.cosmology)
        power_spectrum = eisenstein_hu(wavenumber, self.A_s, self.n_s,
                                       self.cosmology, kwmap=self.kwmap,
                                       wiggle=self.wiggle)
        shape = np.shape(redshift) + np.shape(wavenumber)
        pzk = (np.square(growth_function)[:, np.newaxis] *
               power_spectrum).reshape(shape)

        if np.isscalar(wavenumber) and np.isscalar(redshift):
            pzk = pzk.item()
        return pzk