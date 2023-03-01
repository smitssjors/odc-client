# odc-client

A small CLI tool to help with working with the ODC Server used in 2AMD15.

# Installation

The package is available on [PyPi](https://pypi.org/project/odc-client/).

```bash
pip install odc-client
```

# Usage

First initialize the configuration file

```bash
odc-client init
```

This command will prompt you for the required information. Next, you can submit your project using

```bash
odc-client submit
```

It will automatically try to detect whether you have a Java or Python project by checking for a `pom.xml` file.
For more information use the `--help` flag. It also supports uploading the data files.
