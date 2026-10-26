"""railflow - GB rail trip distribution and network flow model.

Builds an average-weekday and annual station-to-station rail trip matrix for
Great Britain from ORR station usage, calibrates region-level deterrence
functions to ORR local-authority journey data, fuses the result with ORR's
observed flows, and assigns it to an OpenStreetMap rail network.
"""
__version__ = "0.1.0"
