# trias-extractor

Parse offers from Trias to the _offer cache_ schema.

Adding Trias requests to a `trias` folder in the repository root, the `load.sh` script can be used to automatically launch the _trias-extractor_ service, the _offer cache_ and parse the files. The _offer cache_ data are persisted in the `./redis-data` folder.
