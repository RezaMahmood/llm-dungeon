'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const stream = require('stream');
const crypto = require('crypto');
const { promisify } = require('util');

const pipeline = promisify(stream.pipeline);
const { writeFile, rm } = fs.promises;

const randomId = () =>
  typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID().replace(/-/g, '')
    : crypto.randomBytes(16).toString('hex');
const getPath = (prefix = '') => path.join(os.tmpdir(), prefix + randomId());

const writeStream = async (filePath, data) => pipeline(data, fs.createWriteStream(filePath));

const removePath = async (targetPath) => {
  if (typeof rm === 'function') {
    await rm(targetPath, { recursive: true, force: true });
    return;
  }

  await fs.promises.rmdir(targetPath, { recursive: true });
};

const createTask = (tempyFunction, { extraArguments = 0 } = {}) => async (...arguments_) => {
  const [callback, options] = arguments_.slice(extraArguments);
  const result = await tempyFunction(...arguments_.slice(0, extraArguments), options);

  try {
    return await callback(result);
  } finally {
    await removePath(result);
  }
};

module.exports.file = (options) => {
  options = {
    ...options,
  };

  if (options.name) {
    if (options.extension !== undefined && options.extension !== null) {
      throw new Error('The `name` and `extension` options are mutually exclusive');
    }

    return path.join(module.exports.directory(), options.name);
  }

  return (
    getPath() +
    (options.extension === undefined || options.extension === null
      ? ''
      : `.${options.extension.replace(/^\./, '')}`)
  );
};

module.exports.file.task = createTask(module.exports.file);

module.exports.directory = ({ prefix = '' } = {}) => {
  const directory = getPath(prefix);
  fs.mkdirSync(directory);
  return directory;
};

module.exports.directory.task = createTask(module.exports.directory);

module.exports.write = async (data, options) => {
  const filename = module.exports.file(options);
  const write = data && typeof data.pipe === 'function' ? writeStream : writeFile;
  await write(filename, data);
  return filename;
};

module.exports.write.task = createTask(module.exports.write, { extraArguments: 1 });

module.exports.writeSync = (data, options) => {
  const filename = module.exports.file(options);
  fs.writeFileSync(filename, data);
  return filename;
};

Object.defineProperty(module.exports, 'root', {
  get() {
    return os.tmpdir();
  },
});
