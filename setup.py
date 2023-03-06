from setuptools import setup, find_packages
from distutils.util import convert_path

setup(name = "figure_inspector",
    version = 0.1,
    description = "Visual Inspection TOol",
    author = "Dom Rowan",
    author_email = "",
    url = "https://github.com/dmrowan/figure_inspector",
    packages = find_packages(include=['figure_inspector', 'figure_inspector.*']),
    package_data = {'figure_inspector':['data/*']},
    include_package_data = True,
    classifiers=[
      'Intended Audience :: Science/Research',
      'Operating System :: OS Independent',
      'Programming Language :: Python :: 3',
      'License :: OSI Approved :: MIT License',
      'Topic :: Scientific/Engineering :: Astronomy'
      ],
    zip_safe=False,
    python_requires=">=3.6",
    install_requires=["astropy", "matplotlib", "numpy", "pandas", "scipy"]
)
