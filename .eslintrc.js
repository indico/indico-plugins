/* eslint-disable import/no-commonjs, import/unambiguous */
/* global module:false, __dirname:false */

const path = require('path');
const fs = require('fs');
const {execSync} = require('child_process');
const _ = require('lodash');
const resolve = require('resolve');
const yaml = require('js-yaml');

// Returns the path to the Indico source package/repo
const PATH_COMMAND = `python -c 'from flask.helpers import get_root_path; print(get_root_path("indico"))'`;

let indicoBaseDir = null;
const indicoPathFile = path.join(__dirname, '.indico_source');

// If there's an .indico_source file in the same dir, let's use it
if (fs.existsSync(indicoPathFile)) {
  indicoBaseDir = fs
    .readFileSync(indicoPathFile)
    .toString()
    .trim();
}

// Otherwise, let's use Python to figure it out
if (!indicoBaseDir) {
  // Figure out where the Indico code base has been set up
  indicoBaseDir = path.join(
    execSync(PATH_COMMAND, {
      encoding: 'utf8',
    }).trim(),
    '..'
  );
}

let currentMap = [];
let defaultConfig = {};

try {
  defaultConfig = yaml.safeLoad(fs.readFileSync(path.join(indicoBaseDir, '.eslintrc.yml')));
  currentMap = defaultConfig.settings['import/resolver'].alias.map;
} catch (e) {
  console.error(e);
}

const reactPath = resolve.sync('react', {basedir: indicoBaseDir});
const react = require(reactPath);
const babelConfigFile = path.join(indicoBaseDir, 'babel.config.js');

module.exports = _.merge(defaultConfig, {
  settings: {
    'react': {
      version: react.version,
    },
    'import/resolver': {
      alias: {
        map: currentMap.map(([k, v]) => [k, path.resolve(indicoBaseDir, v)]),
      },
      node: {
        paths: path.join(indicoBaseDir, 'node_modules'),
      },
    },
  },
  parserOptions: {
    babelOptions: {
      configFile: babelConfigFile
    }
  }
});
