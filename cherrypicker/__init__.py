__author__ = 'chm'
import os

module_root_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.abspath(os.path.join(module_root_dir, os.path.pardir))
data_dir = os.path.join(project_dir, 'data')