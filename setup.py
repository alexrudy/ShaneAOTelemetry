from setuptools import setup

setup(name="telemetry",
      version="0.0",
      author="Alexander Rudy",
      author_email="arrudy@ucsc.edu",
      packages=["telemetry"],
      entry_points = {
          'console_scripts':[
              'telemetry = telemetry.cli:cli'
          ]
      }
      )
