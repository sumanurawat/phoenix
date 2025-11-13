export const installMceAutosizeGuard = () => {
  if (typeof window === 'undefined') {
    return;
  }

  const registry = window.customElements;
  if (!registry) {
    return;
  }

  const guardKey = '__phoenixMceGuardInstalled';
  const globalScope = window as unknown as Record<string, unknown>;

  if (globalScope[guardKey]) {
    return;
  }

  const originalDefine = registry.define.bind(registry);
  const patchedDefine: typeof registry.define = (name, constructor, options) => {
    if (name === 'mce-autosize-textarea' && registry.get(name)) {
      if (import.meta.env.DEV) {
        console.warn('Skipping duplicate registration of mce-autosize-textarea');
      }
      return;
    }

    originalDefine(name, constructor, options);
  };

  registry.define = patchedDefine;
  globalScope[guardKey] = true;
};
