.. OSeMOSYS-RDM documentation master file

==================================
OSeMOSYS-RDM Documentation
==================================

**OSeMOSYS-RDM** is a reproducible workflow tool for **preprocessing, solving, and postprocessing** 
models built with the **OSeMOSYS** (Open Source Energy Modelling System) architecture, with built-in 
support for **Robust Decision Making (RDM)** style exploratory ensembles and **scenario discovery** (PRIM).

.. image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
   :target: https://opensource.org/licenses/Apache-2.0
   :alt: License

.. image:: https://readthedocs.org/projects/osemosys-rdm/badge/?version=latest
   :target: https://osemosys-rdm.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. note::
   
   This project is under active development. Contributions are welcome!

Key Features
------------

- **Two operation modes**: Base Future mode for single baseline scenarios and RDM Experiment mode 
  for uncertainty analysis with Latin Hypercube Sampling
  
- **Multi-solver support**: GLPK (required), CBC, CPLEX, and Gurobi

- **End-to-end automation**: From preprocessing through solving to consolidated datasets

- **Scenario discovery**: Integrated PRIM workflow for identifying parameter ranges

- **Reproducible pipelines**: DVC-based dependency tracking and caching

Quick Links
-----------

- **Source Code**: `GitHub Repository <https://github.com/clg-admin/osemosys-rdm>`_
- **Issue Tracker**: `GitHub Issues <https://github.com/clg-admin/osemosys-rdm/issues>`_
- **OSeMOSYS**: `Official Website <https://www.osemosys.org/>`_

.. toctree::
   :maxdepth: 2
   :caption: Getting Started
   :hidden:

   getting-started/installation
   getting-started/quickstart
   getting-started/configuration

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   :hidden:

   user-guide/workflow-overview
   user-guide/rdm-pipeline
   user-guide/prim-analysis
   user-guide/interface-configuration
   user-guide/dvc-integration

.. toctree::
   :maxdepth: 2
   :caption: Tutorials
   :hidden:

   tutorials/basic-run
   tutorials/uncertainty-analysis
   tutorials/scenario-discovery

.. toctree::
   :maxdepth: 2
   :caption: Results & Examples
   :hidden:

   results/index

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide
   :hidden:

   developer-guide/architecture
   developer-guide/extending
   developer-guide/contributing

.. toctree::
   :maxdepth: 1
   :caption: Reference
   :hidden:

   api/index
   changelog
   license

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
