import React from 'react';
import { Link } from 'react-router-dom';

const Navbar = () => {
  return (
    <nav className="bg-navbar-bg text-navbar-text h-16 shadow-md sticky top-0 z-50 transition-colors duration-300">
      <div className="max-w-7xl mx-auto flex justify-between items-center h-full px-6 md:px-10">
        <Link
          to="/"
          className="text-2xl md:text-3xl font-bold tracking-tight text-white hover:text-navbar-accent transition-colors"
        >
          Jaguar Interface
        </Link>
        <ul className="flex space-x-6 text-sm md:text-base font-medium">
          <li>
            <Link
              to="/dashboard"
              className="text-navbar-text hover:text-navbar-accent transition-colors"
            >
              Dashboard
            </Link>
          </li>
          <li>
            <Link
              to="/debug"
              className="text-navbar-text hover:text-navbar-accent transition-colors"
            >
              Debug Panel
            </Link>
          </li>
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;
