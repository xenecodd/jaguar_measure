import React from 'react';
import { Link } from 'react-router-dom';

const Navbar = () => {
  return (
    <nav className="bg-navbar-bg text-navbar-text h-16 shadow-md sticky top-0 z-50 transition-colors duration-300">
      <div className="container mx-auto flex justify-between items-center h-full px-8">
        <Link to="/" className="text-3xl font-semibold text-white hover:text-navbar-accent">
          Jaguar Interface
        </Link>
        <ul className="flex space-x-4">
          <li><Link to="/dashboard" className="text-navbar-text hover:text-navbar-accent">Dashboard</Link></li>
          <li><Link to="/debug" className="text-navbar-text hover:text-navbar-accent">Debug Panel</Link></li>
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;
