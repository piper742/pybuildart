# pybuildart

A declerative BUILD engine ART file creator written in Python.

## Description

Created for a now abandoned project in EDuke32, this program was designed as a replacement
for the clunky prototyping solutions for development eg.: tilefromtexture, BAFed.

Features:
- Declerative properties for tiles
- Wide range of image formats supported (including animated ones)
- Palettization during build
- Improved image downscaling (via the Rapid, Detail-Preserving Image Downscaling algorithm)
- Saturation correction for input images

## Getting started

### Dependencies

- Python 3.9+
- toml 0.10.2
- Pillow

### Usage

The program requires a directory named after the output's number (TILES###.ART),
and a PALETTE.DAT in the (current) directory containing that directory.
The program must be executed with the name of the directory. Eg.:
```
$ pybuildart 000/
```
After the first run of the program a config.toml file will appear in the numbered directory.
Running the program without any arguments gives a help message describing all possible options
in the config.toml file.
Tile IDs must be specified in the config file within quotes. They can be seperated by commas (,),
or made to be a ranged decleration via dashes (-) (these must also be located within the quotes).
Single tile declerations will always override options specified by ranged declerations.

## Acknowledgements

This program contains an adapted implementation of the following paper:

Weber, N., Waechter, M., Amend, S., Guthe, S., Goesele, M. 2016. Rapid, Detail-Preserving Image Down-
scaling. ACM Trans. Graph. 35, 6, Article 205 (November 2016), 6 pages.
DOI = 10.1145/2980179.2980239

http://doi.acm.org/10.1145/2980179.2980239.
