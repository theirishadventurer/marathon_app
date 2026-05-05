import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'marathon.auth.token';
const EXPIRES_KEY = 'marathon.auth.expires_at';

export async function saveAuth(token: string, expiresAtIso: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
  await SecureStore.setItemAsync(EXPIRES_KEY, expiresAtIso);
}

export async function loadToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function loadExpiresAt(): Promise<Date | null> {
  const raw = await SecureStore.getItemAsync(EXPIRES_KEY);
  return raw ? new Date(raw) : null;
}

export async function clearAuth(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(EXPIRES_KEY);
}
