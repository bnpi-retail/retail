import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Contact from "./pages/Contact";

import { createTheme, MantineProvider } from '@mantine/core';
import '@mantine/core/styles.css';

const theme = createTheme({
  /** Put your mantine theme override here */
});

export default function App() {
  return (
    <BrowserRouter>
      <MantineProvider theme={theme}>
        <Routes>
          <Route path="/">
            <Route path="contact" element={<Contact />} />
          </Route>
        </Routes>
      </MantineProvider>
    </BrowserRouter>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);