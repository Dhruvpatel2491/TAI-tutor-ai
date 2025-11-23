import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import ProtectedRoute from '../components/ProtectedRoute';
import { authService } from '../services/authService';

function Dummy() { return <div>Protected</div>; }

test('redirects to /login when not authenticated', () => {
  // ensure no session
  authService.logout();

  render(
    <MemoryRouter initialEntries={["/protected"]}>
      <Routes>
        <Route path="/login" element={<div>Login page</div>} />
        <Route path="/protected" element={<ProtectedRoute><Dummy /></ProtectedRoute>} />
      </Routes>
    </MemoryRouter>
  );

  expect(screen.getByText(/Login page/i)).toBeTruthy();
});
