export function Footer() {
  return (
    <footer className="bg-gray-5 border-t border-gray-10 mt-auto">
      <div className="max-w-5xl mx-auto px-4 py-6 text-center text-sm text-gray-60">
        &copy; {new Date().getFullYear()} Calyx Containers. All rights
        reserved.
      </div>
    </footer>
  );
}
