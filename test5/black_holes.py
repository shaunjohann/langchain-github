import math

def compute_evaporation_time(mass):
    G = 6.6743e-11  # m^3 / (kg * s^2)
    hbar = 1.0546e-34  # J * s
    c = 2.9979e8  # m / s
    mass_kg = mass
    if isinstance(mass, str) and 'kg' in mass:
        mass_kg = float(mass.replace('kg', ''))
    elif isinstance(mass, str) and 'g' in mass:
        mass_kg = float(mass.replace('g', '')) / 1000
    elif isinstance(mass, str) and 'mg' in mass:
        mass_kg = float(mass.replace('mg', '')) / 1e+6
    elif isinstance(mass, str) and 'M' in mass:
        mass_kg = float(mass.replace('M', '')) * 1e+6
    elif isinstance(mass, str) and 'm' in mass:
        mass_kg = float(mass.replace('m', '')) / 1e+3
    elif isinstance(mass, str) and 't' in mass:
        mass_kg = float(mass.replace('t', '')) * 1000
    t = 5120 * math.pi * G**2 * mass_kg**3 / (hbar * c**4)
    return t
