import { authService } from '../services/authService';

test('derivePasswordHash is deterministic for same password and salt', async () => {
  const password = 'CorrectHorseBatteryStaple';
  const salt = 'c2FsdGJ5dGVzMTIzNDU='; // base64 of 'saltbytes12345'
  const hash1 = await authService.derivePasswordHash(password, salt);
  const hash2 = await authService.derivePasswordHash(password, salt);
  expect(hash1).toBe(hash2);
});
