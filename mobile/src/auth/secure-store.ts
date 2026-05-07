import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const TOKEN_KEY = 'marathon.auth.token';
const EXPIRES_KEY = 'marathon.auth.expires_at';

const isWeb = Platform.OS === 'web';

async function setItem(key: string, value: string): Promise<void> {
  if (isWeb) {
    if (typeof globalThis.localStorage !== 'undefined') {
      globalThis.localStorage.setItem(key, value);
    }
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

async function getItem(key: string): Promise<string | null> {
  if (isWeb) {
    if (typeof globalThis.localStorage !== 'undefined') {
      return globalThis.localStorage.getItem(key);
    }
    return null;
  }
  return SecureStore.getItemAsync(key);
}

async function deleteItem(key: string): Promise<void> {
  if (isWeb) {
    if (typeof globalThis.localStorage !== 'undefined') {
      globalThis.localStorage.removeItem(key);
    }
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

export async function saveAuth(token: string, expiresAtIso: string): Promise<void> {
  await setItem(TOKEN_KEY, token);
  await setItem(EXPIRES_KEY, expiresAtIso);
}

export async function loadToken(): Promise<string | null> {
  return getItem(TOKEN_KEY);
}

export async function loadExpiresAt(): Promise<Date | null> {
  const raw = await getItem(EXPIRES_KEY);
  return raw !== null ? new Date(raw) : null;
}

export async function clearAuth(): Promise<void> {
  await deleteItem(TOKEN_KEY);
  await deleteItem(EXPIRES_KEY);
}
