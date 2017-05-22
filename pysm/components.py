"""                                                                                            
.. module:: components
   :platform: Unix
   :synopsis: module containing definitions of component objects in pysm.

.. moduleauthor: Ben Thorne <ben.thorne@physics.ox.ac.uk>                                       
"""

import numpy as np
import healpy as hp
import os, sys, time
import scipy.constants as constants
from scipy.interpolate import interp1d, RectBivariateSpline
from scipy.misc import factorial, comb
from common import read_key, convert_units, FloatOrArray, invert_safe

class Synchrotron(object):
    """Class defining attributes and scaling laws of the synchrotron 
    component, instantiated with a configuration dictionary containing
    the required parameters of the synchrotron models. The key
    item pairs are then assigned as attributes. 

    The current possible attributes are:

    - `Model` : SED used, power law or curved power law. 
    - `A_I` : intensity template used -- numpy.ndarray or float.
    - `A_Q` : Q template used -- numpy.ndarray or float.
    - `A_U` : U template used -- numpy.ndarray or float.
    - `Nu_0_I` : reference frequency of I template -- float.
    - `Nu_0_P` : reference frequency of Q and U template -- float.
    - `Spectral_Index` : spectral index used in power law and curved power law -- numpy.ndarray or float.
    - `Spectral_Curvature` -- numpy.ndarray or float.
    - `Nu_Curve` -- pivot frequency of curvature.

    """
    def __init__(self, config):
        for k in config.keys():
            read_key(self, k, config)
        return 

    @property
    def Model(self):
    	try:
            return self.__model
    	except AttributeError:
    	    print("Synchrotron attribute 'Model' not set.")
    	    sys.exit(1)

    @property
    def A_I(self):
    	try:
            return self.__A_I
        except AttributeError:
    	    print("Synchrotron attribute 'A_I' not set.")
    	    sys.exit(1)

    @property
    def A_Q(self):
    	try:
            return self.__A_Q
        except AttributeError:
    	    print("Synchrotron attribute 'A_Q' not set.")
    	    sys.exit(1)

    @property
    def A_U(self):
    	try:
            return self.__A_U
        except AttributeError:
    	    print("%s attribute 'A_U' not set.")
    	    sys.exit(1)

    @property
    def Nu_0_I(self):
    	try:
            return self.__nu_0_I
        except AttributeError:
    	    print("Synchrotron attribute 'Nu_0_I' not set.")
    	    sys.exit(1)

    @property
    def Nu_0_P(self):
    	try:
            return self.__nu_0_P
        except AttributeError:
    	    print("Synchrotron attribute 'Nu_0_P' not set.")
    	    sys.exit(1)

    @property
    def Spectral_Index(self):
    	try:
            return self.__spectral_index
        except AttributeError:
    	    print("Synchrotron attribute 'Spectral_Index' not set.")
    	    sys.exit(1)

    @property
    def Spectral_Curvature(self):
    	try:
            return self.__spectral_curvature
    	except AttributeError:
    	    print("Synchrotron attribute 'Spectral_Curvature' not set.")
    	    sys.exit(1)

    @property
    def Nu_Curve(self):
        try:
            return self.__nu_curve
        except AttributeError:
            print("Synchrotron attribute 'Nu_Curve' not set.")
            sys.exit(1)
            
    def signal(self):
        """Function to return the selected SED.

        :return: function -- selected model SED.

        """
        return getattr(self, self.Model)()
    
    def power_law(self):
        """Returns synchrotron (T, Q, U) maps as a function of observation 
        freuency, nu. 

        This is the simplest model, using only a power law spectral
        dependence.  The map of the spectral index may be a constant
        or spatially varing.

        :return: power law model -- function

        """
        @FloatOrArray
        def model(nu):
            """Power law scaling model. 

            :param nu: frequency at which to calculate the map.
            :type nu: float.
            :return: power law scaled maps, shape (3, Npix) -- numpy.ndarray shape

            """
            scaling_I = power_law(nu, self.Nu_0_I, self.Spectral_Index)
            scaling_P = power_law(nu, self.Nu_0_P, self.Spectral_Index)
            return np.array([self.A_I * scaling_I, self.A_Q * scaling_P, self.A_U * scaling_P])
        return model
    
    def curved_power_law(self):
        """Returns synchrotron (T, Q, U) maps as a function of observation
        frequency, nu. 

        This model allows for curvature of the power law SED. The
        spectral curvature be a constant, or a map.

        :return: power law model -- function 

        """
        @FloatOrArray
        def model(nu):
            """Power law scaling model.
            :param nu: frequency at which to calculate the map.
            :type nu: float.
            :return: power law scaled maps, shape (3, Npix) -- numpy.ndarray shape                                                                                                               
            """
            curvature_term = np.log(power_law(nu, self.Nu_Curve, self.Spectral_Curvature))
            scaling_I = power_law(nu, self.Nu_0_I, self.Spectral_Index + curvature_term)
            scaling_P = power_law(nu, self.Nu_0_P, self.Spectral_Index + curvature_term)
            return np.array([self.A_I * scaling_I, self.A_Q * scaling_P, self.A_U * scaling_P])
        return model
    
class Dust(object):
    """Class defining attributes and scaling laws of the dust                                                   
    component, instantiated with a configuration dictionary containing                                                 
    the required parameters of the synchrotron models. The key                                                         
    item pairs are then assigned as attributes.                                                                        
                                                                                                                       
    The current possible attributes are:                                                                               
                                                                                                                       
    - `Model` : SED used, modified black body, Hensley and Draine 2017.
    - `A_I` : intensity template used -- numpy.ndarray, float.                                                       
    - `A_Q` : Q template used -- numpy.ndarray, float.                                                               
    - `A_U` : U template used -- numpy.ndarray, float.                                                               
    - `Nu_0_I` : reference frequency of I template -- float.                                                           
    - `Nu_0_P` : reference frequency of Q and U template -- float.                                                     
    - `Spectral_Index` : spectral index used in power law and curved power law -- numpy.ndarray, float.                                                                               
    - `Temp` : temperature template used in the modified black body scaling -- numpy.ndarray, float
    - `Uval` : Parameter required by Hensley and Draine model.
    - `Fsilfe` : Parameter required by Hensley and Draine model.
    - `Fcar` : Parameter required by Hensley and Draine model.
    - `Add_Decorrelation` : add stochastic frequency decorrelation to the SED -- bool.
    - `Corr_Len` : correlation length to use in decorrelation model -- float.
    

    """
    def __init__(self, config):
        for k in config.keys():
            read_key(self, k, config)
        return

    @property
    def Model(self):
    	try:
            return self.__model
    	except AttributeError:
    	    print("Dust attribute 'Model' not set.")
    	    sys.exit(1)

    @property
    def A_I(self):
    	try:
            return self.__A_I
        except AttributeError:
    	    print("Dust attribute 'A_I' not set.")
    	    sys.exit(1)

    @property
    def A_Q(self):
    	try:
            return self.__A_Q
        except AttributeError:
    	    print("Dust attribute 'A_Q' not set.")
    	    sys.exit(1)

    @property
    def A_U(self):
    	try:
            return self.__A_U
        except AttributeError:
    	    print("Dust attribute 'A_U' not set.")
    	    sys.exit(1)

    @property
    def Nu_0_I(self):
    	try:
            return self.__nu_0_I
        except AttributeError:
    	    print("Dust attribute 'Nu_0_I' not set.")
    	    sys.exit(1)

    @property
    def Nu_0_P(self):
    	try:
    	    return self.__nu_0_P
        except AttributeError:
    	    print("Dust attribute 'Nu_0_P' not set.")
    	    sys.exit(1)

    @property
    def Spectral_Index(self):
    	try:
	    return self.__spectral_index
        except AttributeError:
    	    print("Dust attribute 'Spectral_Index' not set.")
    	    sys.exit(1)

    @property
    def Temp(self):
    	try:
            return self.__temp
        except AttributeError:
    	    print("Dust attribute 'Temp' not set.")
    	    sys.exit(1)

    @property
    def Uval(self):
        try:
            return self.__uval
        except AttributeError:
            print("Dust attribute 'Uval' not set.")
            sys.exit(1)

    @property
    def Fcar(self):
        try:
            return self.__fcar
        except AttributeError:
            print("Dust attribute 'Fcar' not set.")
            sys.exit(1)

    @property
    def Fsilfe(self):
        try:
            return self.__fsilfe
        except AttributeError:
            print("Dust attribute 'Fsilfe' not set.")
            sys.exit(1)

    @property
    def Corr_Len(self):
        try:
            return self.__corr_len
        except AttributeError:
            print("Dust attribute 'Corr_Len' not set.")
            sys.exit(1)

    @property
    def Add_Decorrelation(self):
        try:
            return self.__add_decorrelation
        except AttributeError:
            print("Dust attribute 'Add_Decorrelation' not set.")
            sys.exit(1)
            
    def signal(self):
        """Function to return the selected SED.
        
        :return: function -- selected scaling model.
        """
        return getattr(self, self.Model)()
    
    def modified_black_body(self):
        """Returns dust (T, Q, U) maps as a function of frequency, nu.
        This is the simplest model, assuming a modified black body SED
        which is the same in temperature and polarisation.

        :return: function -- modified black body function.

        """
        @Add_Decorrelation(self)
        @FloatOrArray
        def model(nu):
            """Black body model 

            :param nu: frequency at which to evaluate model.
            :type nu: float.
            :return: modified black body scaling of maps, shape (3, Npix).
            
            """
            scaling_I = power_law(nu, self.Nu_0_I, self.Spectral_Index) * black_body(nu, self.Nu_0_I, self.Temp)
            scaling_P = power_law(nu, self.Nu_0_P, self.Spectral_Index) * black_body(nu, self.Nu_0_P, self.Temp)
            return np.array([self.A_I * scaling_I, self.A_Q * scaling_P, self.A_U * scaling_P])
        return model

    def hensley_draine_2017(self):
        """Returns dust (T, Q, U) maps as a function of observing frequenvy in GHz, nu. Uses the Hensley and Draine 2017 model.

        :return: function - model (T, Q, U) maps.

        """

        # Define some local constants in cgs units
        # This should be changed in the future as it causes some conflicts
        # at 1e-5 due to mismatch with other constants.
        c = 2.99792458e10
        h = 6.62606957e-27
        k = 1.3806488e-16
        
        # Planck function
        def B_nu (nu, T):
            return 2.0 * h * (nu ** 3) / (c ** 2 * (np.expm1(h * nu / (k * T))))

        # Conversion to K_CMB
        def G_nu (nu, T):
            x = h * nu / (k * T)
            return B_nu(nu, T) * x * np.exp(x) / (np.expm1(x) * T)
        
        # Read in precomputed dust emission spectra as a function of lambda and U
        T_CMB = 2.7255
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pysm', 'template'))
        data_sil = np.genfromtxt(os.path.join(data_dir, "sil_DH16_Fe_00_2.0.dat"))
        data_silfe = np.genfromtxt(os.path.join(data_dir, "sil_DH16_Fe_05_2.0.dat"))
        data_cion = np.genfromtxt(os.path.join(data_dir, "cion_1.0.dat"))
        data_cneu = np.genfromtxt(os.path.join(data_dir, "cneu_1.0.dat"))
        
        wav = data_sil[:, 0]
        uvec = np.linspace(-0.5, 0.5, num = 11, endpoint = True)
            
        sil_i = RectBivariateSpline(uvec, wav, ((data_sil[:, 4 : 15] / (9.744e-27)) * (wav[:, np.newaxis] * 1.e-4 / c) * 1.e23).T) # to Jy
        car_i = RectBivariateSpline(uvec, wav, (((data_cion[:, 4 : 15] + data_cneu[:, 4 : 15]) / (2.303e-27)) * (wav[:, np.newaxis] * 1.e-4 / c) * 1.e23).T) # to Jy
        silfe_i = RectBivariateSpline(uvec, wav, ((data_silfe[:, 4 : 15] / (9.744e-27)) * (wav[:, np.newaxis] * 1.e-4 / c) * 1.e23).T) # to Jy
        
        sil_p = RectBivariateSpline(uvec, wav, ((data_sil[:, 15 : 26] / (9.744e-27)) * (wav[:, np.newaxis] * 1.e-4 / c) * 1.e23).T) # to Jy
        car_p = RectBivariateSpline(uvec, wav, (((data_cion[:, 15 : 26] + data_cneu[:, 4 : 15]) / (2.303e-27)) * (wav[:, np.newaxis] * 1.e-4 / c) * 1.e23).T) # to Jy
        silfe_p = RectBivariateSpline(uvec, wav, ((data_silfe[:, 15 : 26] / (9.744e-27)) * (wav[:, np.newaxis] * 1.e-4 / c)*1.e23).T) # to Jy

        @Add_Decorrelation(self)
        @FloatOrArray
        def model(nu):
            """Model of Hensley and Draine 2017. 

            :param nu: frequency at which to evaluate the model. 
            :type nu: float.
            :return: maps produced using Hensley and Draine 2017 SED. 

            """
            nu *= 1.e9
            nu_to_lambda = lambda x: 1.e4 * c / x # in microns
            lam =  nu_to_lambda(nu)
            lam_ref_I = nu_to_lambda(self.Nu_0_I * 1.e9)
            lam_ref_P = nu_to_lambda(self.Nu_0_P * 1.e9)
            scaling_I = G_nu(self.Nu_0_I * 1.e9, T_CMB) / G_nu(nu, T_CMB) * (sil_i.ev(self.Uval, lam) + self.Fcar * car_i.ev(self.Uval, lam) + self.Fsilfe * silfe_i.ev(self.Uval, lam)) / (sil_i.ev(self.Uval, lam_ref_I) + self.Fcar * car_i.ev(self.Uval, lam_ref_I) + self.Fsilfe * silfe_i.ev(self.Uval, lam_ref_I))
            scaling_P = G_nu(self.Nu_0_P * 1.e9, T_CMB) / G_nu(nu, T_CMB) * (sil_p.ev(self.Uval, lam) + self.Fcar * car_p.ev(self.Uval, lam) + self.Fsilfe * silfe_p.ev(self.Uval, lam)) / (sil_p.ev(self.Uval, lam_ref_P) + self.Fcar * car_p.ev(self.Uval, lam_ref_P) + self.Fsilfe * silfe_p.ev(self.Uval, lam_ref_P))
            return np.array([scaling_I * self.A_I, scaling_P * self.A_Q, scaling_P * self.A_U])
        return model
    
class AME(object):
    """Class defining attributes and scaling laws of the synchrotron                                                   
    component, instantiated with a configuration dictionary containing                                                 
    the required parameters of the synchrotron models. The key                                                         
    item pairs are then assigned as attributes.                                                                        
                                                                                                                       
    The current possible attributes are:                                                                               
                                                                                                                       
    - `Model` : SED used, power law or curved power law.                                                               
    - `A_I` : intensity template used -- numpy.ndarray or float.                                                       
    - `Nu_0_I` : reference frequency of I template -- float.                                                           
    - `Nu_0_P` : reference frequency of Q and U template -- float.                                                     
    - `Emissivity` : numerically computed emissivity used to scale AME. In the nominal models this is produced using the SpDust2 code (Ali-Haimoud 2008) -- numpy.ndarray
    - `Nu_Peak_0` : parameter required by SpDust2 -- float
    - `Nu_Peak` : parameter required by SpDust2 -- float, numpy.ndarray
    - `Pol_Frac` : polarisation fraction used in polarised AME model. 
    - `Angle_Q` : Q template from which to calculate polarisation angle for AME. 
    - `Angle_U` : U template from which to calculate polarisation angle for AME.
                                                                                                                       
    """
    
    def __init__(self, config):
        for k in config.keys():
            read_key(self, k, config)
        return  

    @property 
    def A_I(self):
        try:
            return self.__A_I
        except AttributeError:
            print("AME attribute 'A_I' not set.")
            sys.ext(1)

    @property
    def Emissivity(self):
    	try:
            return self.__emissivity
        except AttributeError:
    	    print("AME attribute 'Emissivity' not set.")
    	    sys.exit(1)

    @property
    def Model(self):
	try:
	    return self.__model
	except AttributeError:
	    print("AME attribute 'Model' not set.")
	    sys.exit(1)

    @property
    def Nu_0_I(self):
    	try:
            return self.__nu_0_I
        except AttributeError:
    	    print("AME attribute 'Nu_0_I' not set.")
    	    sys.exit(1)

    @property
    def Nu_Peak(self):
    	try:
            return self.__nu_peak
        except AttributeError:
    	    print("AME attribute 'Nu_Peak' not set.")
    	    sys.exit(1)

    @property
    def Nu_Peak_0(self):
    	try:
            return self.__nu_peak_0
    	except AttributeError:
    	    print("AME attribute 'Nu_Peak_0' not set.")
    	    sys.exit(1)

    @property
    def Angle_Q(self):
        try:
            return self.__angle_q
        except AttributeError:
            print("AME attribute 'Angle_Q' not set.")
            sys.exit(1)

    @property
    def Angle_U(self):
        try:
            return self.__angle_u
        except AttributeError:
            print("AME attribute 'Angle_U' not set.")
            sys.exit(1)
            
    @property
    def Pol_Frac(self):
    	try:
    	    return self.__pol_frac
    	except AttributeError:
    	    print("AME attribute 'Pol_Frac' not set.")
    	    sys.exit(1)

    def signal(self):
        """Function to return the selected SED.

        :return: function -- selected model SED.

        """
        return getattr(self, self.Model)()
            
    def spdust_scaling(self, nu):
        """Returns AME SED at frequency in GHz, nu. 
        Implementation of the SpDust2 code of (Ali-Haimoud et al 2012), evaluated for a 
        Cold Neutral Medium.

        :param nu: frequency at which to calculate SED.
        :type nu: float.
        :return: spdust SED - float.

        """
    	J = interp1d(self.Emissivity[0], self.Emissivity[1], bounds_error = False, fill_value = 0)
        arg1 = nu * self.Nu_Peak_0 / self.Nu_Peak
        arg2 = self.Nu_0_I * self.Nu_Peak_0 / self.Nu_Peak
        scaling = ((self.Nu_0_I / nu) ** 2) * (J(arg1) / J(arg2))
        return scaling

    def spdust(self):
        """Returns AME (T, Q, U) maps as a function of observing frequency, nu. 
        
        :return: function -- AME spdust2 scaling as a function of frequency.
        """
        @FloatOrArray
        def model(nu):
            """Spdust2 unpolarised model.

            :param nu: frequency in GHz at which to calculate the AME maps using 
            spdust2.
            :type nu: float.
            :return: AME maps at frequency nu, shape (3, Npix) -- numpy.ndarray.

            """
            return np.array([self.spdust_scaling(nu) * self.A_I, np.zeros_like(self.A_I), np.zeros_like(self.A_I)])	
        return model

    def spdust_pol(self):
        """Returns AME (T,Q, U) maps a a function of observing frequency Polarisation 
        version of :meth:`pysm.components.spdust` in which the Q and U templates 
        are calculated using the polarisation angle from the input Q_Angle and 
        U_Angle tepmlates, and the given Pol_Frac.
        Scaling is the same as spdust(self).

        :return: function -- polarised spdust2 model as a function of frequency.
        """
        @FloatOrArray
    	def model(nu):
            """We use input Q and U from dust templates in order to make the
            polarisation angle consistent after down or up grading
            resolution. Downgrading polarisatoin angle templates gives
            a different result to downgrading Q and U maps then
            calculating polarisation angle.

            :param nu: frequency in GHz at which to evaluate the model.
            :type nu: float. 
            :return: numpy.ndarray -- maps of polarised AME model, shape (3, Npix).

            """
            pol_angle = np.arctan2(self.Angle_U, self.Angle_Q)
    	    A_Q = self.A_I * self.Pol_Frac * np.cos(pol_angle)
    	    A_U = self.A_I * self.Pol_Frac * np.sin(pol_angle)
    	    return self.spdust_scaling(nu) * np.array([self.A_I, A_Q, A_U])
    	return model

class Freefree(object):
    """Class defining attributes and scaling laws of the free-free
    component, instantiated with a configuration dictionary containing                                                 
    the required parameters of the free-free models. The key                                                         
    item pairs are then assigned as attributes.                                                                        
                                                                                                                       
    The current possible attributes are:                                                                               
                                                                                                                       
    - `Model` : SED used, for free-free only power law is available.                                                               
    - `A_I` : intensity template used -- numpy.ndarray or float.                                                       
    - `Nu_0_I` : reference frequency of I template -- float.                                                           
    - `Spectral_Index` : spectral index used in power law and curved power law -- numpy.ndarray or float.                                                                               
                                                                           
    """
    def __init__(self, config):
	for k in config.keys():
	    read_key(self, k, config)
	return

    @property
    def Model(self):
	try:
	    return self.__model
	except AttributeError:
	    print("Freefree attribute 'Model' not set.")
	    sys.exit(1)
            
    @property
    def A_I(self):
	try:
	    return self.__A_I
	except AttributeError:
	    print("Freefree attribute 'A_I' not set.")
	    sys.exit(1)

    @property
    def Nu_0_I(self):
	try:
	    return self.__nu_0_I
	except AttributeError:
	    print("Freefree attribute 'Nu_0_I' not set.")
	    sys.exit(1)

    @property
    def Spectral_Index(self):
	try:
	    return self.__spectral_index
	except AttributeError:
	    print("Freefree attribute 'Spectral_Index' not set.")
	    sys.exit(1)

    def signal(self):
        """Function to return the selected SED.                                                                        
                                                                                                                       
        :return: function -- selected scaling model.
        """
	return getattr(self, self.Model)()
	
    def power_law(self):
        """Returns synchrotron (T, Q, U) maps as a function of observation                                             
        freuency, nu.                                                                                                  
                                                                                                                       
        This is the simplest model, using only a power law spectral                                                    
        dependence.  The map of the spectral index may be a constant                                                   
        or spatially varing.                                                                                           
                                                                                                                       
        :return: function -- power law model.
                                                                                           
        """
        @FloatOrArray
	def model(nu):
            """Power law scaling model.

            :param nu: frequency at which to calculate the map.                                                        
            :type nu: float.                                                                                           
            :return: numpy.ndarray -- power law scaled maps, shape (3, Npix).
                                                                                                        
            """
	    scaling = power_law(nu, self.Nu_0_I, self.Spectral_Index)
	    zeros = np.zeros_like(self.A_I)
	    return np.array([self.A_I * scaling, zeros, zeros])
	return model

class CMB(object):
    """Class defining attributes and scaling laws of the synchrotron                                                   
    component, instantiated with a configuration dictionary containing                                                 
    the required parameters of the synchrotron models. The key                                                         
    item pairs are then assigned as attributes.

    The current possible attributes are:

    - `Model` : SED law, e.g. taylens.
    - `A_I` : intensity template used -- numpy.ndarray or float.                                                       
    - `A_Q` : Q template used -- numpy.ndarray or float.                                                               
    - `A_U` : U template used -- numpy.ndarray or float.                                                               
    - `cmb_specs` : input cls in CAMB format -- numpy.ndarray
    - `delensing_ells` : delensing fraction as a function of ell -- numpy.ndarray
    - `nside` : nside at which to generate CMB. 
    - `cmb_seed` : random seed for CMB generation.
                                                                                                                
    """
    def __init__(self, config):
	for k in config.keys():
	    read_key(self, k, config)
	return

    @property
    def Model(self):
	try:
	    return self.__model
	except AttributeError:
	    print("CMB attribute 'Model' not set.")
	    sys.exit(1)

    @property
    def CMB_Specs(self):
	try:
	    return self.__cmb_specs
	except AttributeError:
	    print("CMB attribute 'CMB_Specs' not set.")
	    sys.exit(1)

    @property 
    def Delens(self):
	try:
	    return self.__delens
	except AttributeError:
	    print("CMB attribute 'Delens' not set.")
	    sys.exit(1)

    @property 
    def Delensing_Ells(self):
	try:
	    return self.__delensing_ells
	except AttributeError:
	    print("CMB attribute 'Delensing_Ells' not set.")
	    sys.exit(1)

    @property 
    def Nside(self):
	try:
	    return self.__nside
	except AttributeError:
	    print("CMB attribute 'Nside' not set.")
	    sys.exit(1)

    @property 
    def CMB_Seed(self):
	try:
	    return self.__cmb_seed
	except AttributeError:
	    print("CMB attribute 'CMB_Seed' not set.")
	    sys.exit(1)

    @property
    def A_I(self):
        try:
            return self.__A_I
        except AttributeError:
            print("CMB attribute 'A_I' not set.")

    @property
    def A_Q(self):
        try:
            return self.__A_Q
        except AttributeError:
            print("CMB attribute 'A_Q' not set.")

    @property
    def A_U(self):
        try:
            return self.__A_U
        except AttributeError:
            print("CMB attribute 'A_U' not set.")
            
    def signal(self):
        """Function to return the selected SED.

        :return: function -- selected model SED.
        
        """
	return getattr(self, self.Model)() 
	
    def taylens(self):
        """Returns CMB (T, Q, U) maps as a function of observing frequency, nu.

        This code is extracted from the taylens code (reference).

        :return: function -- CMB maps.
        """
	synlmax = 8 * self.Nside #this used to be user-defined.
	data = self.CMB_Specs
	lmax_cl = len(data[0]) + 1
	l = np.arange(int(lmax_cl + 1))
	synlmax = min(synlmax, l[-1])

	#Reading input spectra in CAMB format. CAMB outputs l(l+1)/2pi hence the corrections.
	cl_tebp_arr=np.zeros([10, lmax_cl + 1])
	cl_tebp_arr[0, 2:] = 2 * np.pi * data[1] / (l[2:] * (l[2:] + 1))    #TT
	cl_tebp_arr[1, 2:] = 2 * np.pi * data[2] / (l[2:] * (l[2:] + 1))    #EE
	cl_tebp_arr[2, 2:] = 2 * np.pi * data[3] / (l[2:] * (l[2:] + 1))    #BB
	cl_tebp_arr[4, 2:] = 2 * np.pi * data[4] / (l[2:] * (l[2:] + 1))    #TE
	cl_tebp_arr[5, :] = np.zeros(lmax_cl + 1)           				#EB
	cl_tebp_arr[7, :] = np.zeros(lmax_cl + 1)                    		#TB

	if self.Delens:
	    cl_tebp_arr[3, 2:] = 2 * np.pi * data[5] * self.Delensing_Ells[1] / (l[2:] * (l[2:] + 1)) ** 2   			#PP
	    cl_tebp_arr[6,:] = np.zeros(lmax_cl + 1)                    												#BP
	    cl_tebp_arr[8, 2:] = 2 * np.pi * data[7] * np.sqrt(self.Delensing_Ells[1]) / (l[2:] * (l[2:] + 1)) ** 1.5   #EP
	    cl_tebp_arr[9, 2:] = 2 * np.pi * data[6] * np.sqrt(self.Delensing_Ells[1]) / (l[2:] * (l[2:] + 1)) ** 1.5  	#TP
	else: 
	    cl_tebp_arr[3,2:] = 2 * np.pi * data[5] / (l[2:] * (l[2:] + 1)) ** 2   	#PP
	    cl_tebp_arr[6,:] =np.zeros(lmax_cl+1)                    				#BP
	    cl_tebp_arr[8,2:] = 2 * np.pi * data[7] / (l[2:] * (l[2:] + 1)) ** 1.5 	#EP
	    cl_tebp_arr[9,2:] = 2 * np.pi * data[6] / (l[2:] * (l[2:] + 1)) ** 1.5 	#TP

	# Coordinates of healpix pixel centers
	ipos = np.array(hp.pix2ang(self.Nside, np.arange(12 * (self.Nside ** 2))))

	# Simulate a CMB and lensing field
	cmb, aphi = simulate_tebp_correlated(cl_tebp_arr, self.Nside, synlmax, self.CMB_Seed)
		
	if cmb.ndim == 1: 
	    cmb = np.reshape(cmb, [1, cmb.size])

	# Compute the offset positions
	phi, phi_dtheta, phi_dphi = hp.alm2map_der1(aphi, self.Nside, lmax = synlmax)

	del aphi
		
	opos, rot = offset_pos(ipos, phi_dtheta, phi_dphi, pol=True, geodesic=False) #geodesic used to be used defined.
	del phi, phi_dtheta, phi_dphi

	# Interpolate maps one at a time
	maps  = []
	for comp in cmb:
	    for m in taylor_interpol_iter(comp, opos, 3, verbose=False, lmax=None): #lmax here needs to be fixed. order of taylor expansion is fixed to 3.
		pass
	    maps.append(m)
	del opos, cmb
	#save the map computed for future referemce.
	rm = apply_rotation(maps, rot)

        @FloatOrArray
	def model(nu):
	    return np.array(rm) * convert_units("uK_CMB", "uK_RJ", nu)
	return model

    def pre_computed(self):
        """Returns a CMB (T, Q, U) maps as a function of observing frequency, nu. 

        This function takes a pre-computed map of the CMB and scales
        it to some new frequency.

        """
        @FloatOrArray
	def model(nu):
	    return np.array([self.A_I, self.A_Q, self.A_U]) * convert_units("uK_CMB", "uK_RJ", nu) 
        return model

def power_law(nu, nu_0, b):
    """Calculate scaling factor for power-law SED.

    Returns a power law scaling by index b for a map at reference
    frequency nu_0 t0 be scale to frequency nu.

    :param nu: frequency being scaled to. 
    :type nu: float.
    :param nu_0: reference frequency of power law. 
    :type nu_0: float. 
    :param b: spectral index by which to scale. 
    :type b: float.

    """
    return (nu / nu_0) ** b

def black_body(nu, nu_0, T):
    """Calculate scaling factor for black body SED.

    Factor to scale a black body emitter of temperature T template
    from frequency nu_0 to frequency nu.

    :param nu: frequency being scaled to.
    :type nu: float.
    :param nu_0: reference frequency of power law.
    :type nu_0: float.
    :param T: temperature of black body function used to scale.
    :type T: float.
    :return: float -- black body at temperature T scaling from frequency nu_0 to nu.

    """
    exp = lambda x: np.exp(-constants.h * x * 1.e9 / constants.k / T)
    return nu / nu_0 * exp(nu) / exp(nu_0) * (exp(nu_0) - 1.) / (exp(nu) - 1.)

def get_decorrelation_matrices(freqs,freq_ref,corrlen) :
    """Function to compute the mean and covariance for the decorrelation
    
    :param freqs: frequencies at which to calculate covariance structure.
    :type freqs: numpy.array.
    :param freq_ref: reference frequency for constrained map.
    :type freq_ref: float.
    :corrlen: correlation length of imposed Gaussian decorrelation.
    :return: numpy.ndarray(len(freqs), len(freqs)), nump.ndarray(len(freqs)) -- the output covariance and mean.
    
    """
    if corrlen <= 0:
        rho_mean = np.ones([len(freqs), 1])
        rho_covar = np.zeros([len(freqs), len(freqs)])
    else:
        added_freq = False
        freqtot = np.array([f for f in freqs])
        if not (freq_ref in freqtot):
            freqtot = np.insert(freqtot, 0, freq_ref)
            added_freq = True
        indref = np.where(freqtot == freq_ref)[0][0]
            
        corrmatrix = np.exp(-0.5 * ((np.log(freqtot[:, None]) - np.log(freqtot[None, :])) / corrlen) ** 2)
        rho_inv = invert_safe(corrmatrix)
        rho_uu = np.delete(np.delete(rho_inv, indref, axis = 0), indref, axis = 1)
        rho_uu = invert_safe(rho_uu)
        rho_inv_cu = rho_inv[:, indref]
        rho_inv_cu=np.transpose(np.array([np.delete(rho_inv_cu, indref)]))
        rho_uu_w, rho_uu_v = np.linalg.eigh(rho_uu)
    
        rho_covar=np.dot(rho_uu_v, np.dot(np.diag(np.sqrt(np.maximum(rho_uu_w, np.zeros_like(rho_uu_w)))), np.transpose(rho_uu_v)))
        rho_mean=-np.dot(rho_uu, rho_inv_cu)
        
        if not added_freq:
            rho_covar_new=np.zeros([len(freqtot), len(freqtot)])
            rho_mean_new=np.ones([len(freqtot), 1])
            rho_covar_new[:indref, :indref] = rho_covar[:indref,:indref]
            rho_covar_new[indref + 1:, :indref] = rho_covar[indref:, :indref]
            rho_covar_new[:indref, indref + 1:] = rho_covar[:indref, indref:]
            rho_covar_new[indref + 1:, indref + 1:] = rho_covar[indref:, indref:]
            rho_covar = rho_covar_new
            rho_mean_new[:indref, :] = rho_mean[:indref, :]
            rho_mean_new[indref + 1:, :] = rho_mean[indref:, :]
            rho_mean = rho_mean_new
            
    return rho_covar, rho_mean

def Add_Decorrelation(Component):
    """Function to calculate a wrapper for some model(nu) function to add
    decorrelation.
                    
    :param Component: instance of one of the classes in :mod:`pysm.component`
    :type Component: class
    :return: function - decorator used to add stochastic decorrelation to an emission model.

    Required parameters:
    
    - Component.Add_Decorrelation: bool - True = add decorrelation. Flase = do not.
    - Component.Corr_Len: float - correlation length defined in accompanying paper.

    Example use:
    .. code-block::
       
       class Synchrotron(object): 
       
       def curved_power_law(self):
           @Add_Decorrelation(self)
           def model(nu):
               return np.array([T, Q, U])
           return model

    """
    if Component.Add_Decorrelation:
        def decorrelation(model):
            """This is the actual decorrelation decorator that will be implemented
            once the add_decorrelation function is evaluated.

            """
            def wrapper(nu):
                N_freqs = len(nu)
                rho_cov_I, rho_m_I = get_decorrelation_matrices(nu, Component.Nu_0_I, Component.Corr_Len)
                rho_cov_P, rho_m_P = get_decorrelation_matrices(nu, Component.Nu_0_P, Component.Corr_Len)
                extra_I = np.dot(rho_cov_I, np.random.randn(N_freqs))
                extra_P = np.dot(rho_cov_P, np.random.randn(N_freqs))
                decorr = np.zeros((N_freqs, 3))
                decorr[:, 0, None] = rho_m_I + extra_I[:, None]
                decorr[:, 1, None] = rho_m_P + extra_P[:, None]
                decorr[:, 2, None] = rho_m_P + extra_P[:, None]
                return decorr[..., None] * model(nu)
            return wrapper
        return decorrelation

    else:
        """If decorrelation not required do nothing with the decorator."""
        def decorrelation(model):
            def wrapper(nu):
                return model(nu)
            return wrapper
        return decorrelation
    
"""The following code is edited from the taylens code: Naess,
S. K. and Louis, T. 2013 'Lensing simulations by Taylor expansion -
not so inefficient after all' Journal of Cosmology and Astroparticle
Physics September 2013.  Available at:
https://github.com/amaurea/taylens

"""                                        
def simulate_tebp_correlated(cl_tebp_arr, nside, lmax, seed):
	"""This generates correlated T,E,B and Phi maps

        """
	np.random.seed(seed)
	alms=hp.synalm(cl_tebp_arr, lmax = lmax, new = True)
	aphi=alms[-1]
	acmb=alms[0 : -1]
	#Set to zero above map resolution to avoid aliasing                                        
	beam_cut=np.ones(3 * nside)
	for ac in acmb:
		hp.almxfl(ac, beam_cut, inplace = True)
	cmb=np.array(hp.alm2map(acmb, nside, pol = True, verbose = False))
	return cmb, aphi
                                                              
def taylor_interpol_iter(m, pos, order=3, verbose=False, lmax=None):
    """Given a healpix map m[npix], and a set of positions
    pos[{theta,phi},...], evaluate the values at those positions using
    harmonic Taylor interpolation to the given order (3 by
    default). Successively yields values for each cumulative order up
    to the specified one. If verbose is specified, it will print
    progress information to stderr.

    """
    nside = hp.npix2nside(m.size)
    if lmax is None: 
    	lmax = 3 * nside
    # Find the healpix pixel centers closest to pos,                                             
    # and our deviation from these pixel centers.                                                
    ipos = hp.ang2pix(nside, pos[0], pos[1])
    pos0 = np.array(hp.pix2ang(nside, ipos))
    dpos = pos[:2] - pos0
    # Take wrapping into account                                                                 
    bad = dpos[1] > np.pi
    dpos[1, bad] = dpos[1, bad] - 2 * np.pi
    bad = dpos[1] <- np.pi
    dpos[1, bad] = dpos[1, bad] + 2 * np.pi

    # Since healpix' dphi actually returns dphi/sintheta, we choose                              
    # to expand in terms of dphi*sintheta instead.                                               
    dpos[1] *= np.sin(pos0[0])
    del pos0

    # We will now Taylor expand our healpix field to                                             
    # get approximations for the values at our chosen                                            
    # locations. The structure of this section is                                                
    # somewhat complicated by the fact that alm2map_der1 returns                                 
    # two different derivatives at the same time.                                                
    derivs = [[m]]
    res = m[ipos]
    yield res
    for o in range(1, order + 1):
            # Compute our derivatives                                                            
            derivs2 = [None for i in range(o+1)]
            used    = [False for i in range(o+1)]
            # Loop through previous level in steps of two (except last)                          
            if verbose: tprint("order %d" % o)
            for i in range(o):
                    # Each alm2map_der1 provides two derivatives, so avoid                       
                    # doing double work.                                                         
                    if i < o-1 and i % 2 == 1:
                            continue
                    a = hp.map2alm(derivs[i], use_weights = True, lmax = lmax, iter = 0)
                    derivs[i] = None
                    dtheta, dphi = hp.alm2map_der1(a, nside, lmax = lmax)[-2:]
                    derivs2[i : i + 2] = [dtheta, dphi]
                    del a, dtheta, dphi
                    # Use these to compute the next level                                        
                    for j in range(i, min(i + 2, o + 1)):
                            if used[j]: 
                            	continue
                            N = comb(o, j) / factorial(o)
                            res += N * derivs2[j][ipos] * dpos[0]**(o-j) * dpos[1]**j
                            used[j] = True
                            # If we are at the last order, we don't need to waste memory         
                            # storing the derivatives any more                                   
                            if o == order: derivs2[j] = None
            derivs = derivs2
            yield res

"""The following functions are support routines for reading input
data and preparing it for being lensed. Most of them are only needed
to take care of tiny, curvature-related effects that can be safely
ignored.

"""                                                                
def readspec(fname):
    """Read a power spectrum with columns [l,comp1,comp2,....]  into a 2d
    array indexed by l. Entries with missing data are filled with
    0.

    """
    tmp = np.loadtxt(fname).T
    l, tmp = tmp[0], tmp[1:]
    res = np.zeros((len(tmp),np.max(l)+1))
    res[:,np.array(l,dtype=int)] = tmp
    return res

def offset_pos(ipos, dtheta, dphi, pol=False, geodesic=False):
    """Offsets positions ipos on the sphere by a unit length step along
    the gradient dtheta, dphi/sintheta, taking the curvature of the
    sphere into account. If pol is passed, also computes the cos and
    sin of the angle by which (Q,U) must be rotated to take into
    account the change in local coordinate system.
                                                                                               
    If geodesic is passed, a quick and dirty, but quite accurate,
    approximation is used.
                                                                                              
    Uses the memory of 2 maps (4 if pol) (plus that of the input
    maps).

    """
    opos = np.zeros(ipos.shape)
    if pol and not geodesic: 
    	orot = np.zeros(ipos.shape)
    else: 
    	orot = None
    if not geodesic:
            # Loop over chunks in order to conserve memory                                       
            step = 0x10000
            for i in range(0, ipos.shape[1], step):
                    small_opos, small_orot = offset_pos_helper(ipos[:,i:i+step], dtheta[i:i+step], dphi[i:i+step], pol)
                    opos[:,i:i+step] = small_opos
                    if pol: orot[:, i : i + step] = small_orot
    else:
            opos[0] = ipos[0] + dtheta
            opos[1] = ipos[1] + dphi / np.sin(ipos[0])
            opos = fixang(opos)
    return opos, orot

def offset_pos_helper(ipos, dtheta, dphi, pol):
    grad = np.array((dtheta, dphi))
    dtheta, dphi = None, None
    d = np.sum(grad ** 2, 0) ** 0.5
    grad  /= d
    cosd, sind = np.cos(d), np.sin(d)
    cost, sint = np.cos(ipos[0]), np.sin(ipos[0])
    ocost  = cosd * cost - sind * sint * grad[0]
    osint  = (1 - ocost ** 2) ** 0.5
    ophi   = ipos[1] + np.arcsin(sind * grad[1] / osint)
    if not pol:
            return np.array([np.arccos(ocost), ophi]), None
    A      = grad[1] / (sind * cost / sint + grad[0] * cosd)
    nom1   = grad[0] + grad[1] * A
    denom  = 1 + A ** 2
    cosgam = 2 * nom1 ** 2 / denom - 1
    singam = 2 * nom1 * (grad[1] - grad[0] * A) / denom
    return np.array([np.arccos(ocost), ophi]), np.array([cosgam,singam])

def fixang(pos):
    """Handle pole wraparound."""
    a = np.array(pos)
    bad = np.where(a[0] < 0)
    a[0,bad] = -a[0, bad]
    a[1,bad] = a[1, bad]+np.pi
    bad = np.where(a[0] > np.pi)
    a[0,bad] = 2 * np.pi - a[0, bad]
    a[1,bad] = a[1, bad] + np.pi
    return a

def apply_rotation(m, rot):
    """Update Q,U components in polarized map by applying the rotation
    rot, represented as [cos2psi,sin2psi] per pixel. Rot is one of the
    outputs from offset_pos.

    """
    if len(m) < 3: 
    	return m
    if rot is None: 
    	return m
    m = np.asarray(m)
    res = m.copy()
    res[1] = rot[0] * m[1] - rot[1] * m[2]
    res[2] = rot[1] * m[1] + rot[0] * m[2]
    return m

# Set up progress prints                                                                             
t0 = None
def silent(msg): 
	pass

def tprint(msg):
        global t0
        if t0 is None: 
        	t0 = time.time()
        print >> sys.stderr, "%8.2f %s" % (time.time() - t0, msg)