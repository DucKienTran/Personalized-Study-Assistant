/**
 * Promise.withResolvers() polyfill
 * Required for pdfjs-dist 4.x on environments where
 * Promise.withResolvers is not yet available.
 */

type PromiseWithResolversResult<T> = {
  promise: Promise<T>;
  resolve: (value: T | PromiseLike<T>) => void;
  reject: (reason?: unknown) => void;
};

const PromiseWithResolvers = Promise as typeof Promise & {
  withResolvers?: <T>() => PromiseWithResolversResult<T>;
};

if (typeof PromiseWithResolvers.withResolvers !== "function") {
  PromiseWithResolvers.withResolvers = function <T>(): PromiseWithResolversResult<T> {
    let resolve!: (value: T | PromiseLike<T>) => void;
    let reject!: (reason?: unknown) => void;

    const promise = new Promise<T>((res, rej) => {
      resolve = res;
      reject = rej;
    });

    return {
      promise,
      resolve,
      reject,
    };
  };
}

export {};