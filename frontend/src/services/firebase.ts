/**
 * Firebase Web Client SDK initialization and Authentication.
 * Safely guards initialization when credentials are not configured.
 */

import { initializeApp, getApps, getApp, FirebaseApp } from 'firebase/app';
import { getAuth, signInWithEmailAndPassword, Auth } from 'firebase/auth';
import { getFirestore, Firestore } from 'firebase/firestore';

const apiKey = (import.meta as any).env?.VITE_FIREBASE_API_KEY;
const authDomain = (import.meta as any).env?.VITE_FIREBASE_AUTH_DOMAIN;
const projectId = (import.meta as any).env?.VITE_FIREBASE_PROJECT_ID;

export function isFirebaseClientConfigured(): boolean {
  return Boolean(
    apiKey &&
    apiKey !== 'your_firebase_api_key' &&
    apiKey !== 'your_firebase_web_api_key' &&
    projectId &&
    projectId !== 'your_firebase_project_id'
  );
}

let appInstance: FirebaseApp | null = null;
let authInstance: Auth | null = null;
let dbInstance: Firestore | null = null;

if (isFirebaseClientConfigured()) {
  const firebaseConfig = {
    apiKey,
    authDomain,
    projectId,
    storageBucket: (import.meta as any).env?.VITE_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: (import.meta as any).env?.VITE_FIREBASE_MESSAGING_SENDER_ID,
    appId: (import.meta as any).env?.VITE_FIREBASE_APP_ID,
  };

  appInstance = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp();
  authInstance = getAuth(appInstance);
  dbInstance = getFirestore(appInstance);
}

export const app = appInstance;
export const auth = authInstance;
export const db = dbInstance;

/**
 * Sign in the owner with Firebase Authentication and return the ID Token.
 */
export async function signInWithFirebase(email: string, pass: string): Promise<string> {
  if (!authInstance) {
    throw new Error('Firebase Web Client is not configured. Please check frontend/.env.');
  }

  const cred = await signInWithEmailAndPassword(authInstance, email, pass);
  return await cred.user.getIdToken();
}
