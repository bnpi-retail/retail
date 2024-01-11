import React, { useState } from 'react';
import { Input, Button, Text } from '@mantine/core';

const AddApiToken = () => {
  const [inputValue, setInputValue] = useState('');

  const handleInputChange = (event) => {
    setInputValue(event.target.value);
  };

  const handleButtonClick = () => {
    localStorage.setItem('apiToken', inputValue);
    chrome.runtime.sendMessage({ type: 'apiTokenSaved', apiToken });
    console.log('API Token saved:', inputValue);
  };

  return (
    <div style={{ maxWidth: 400, margin: 'auto', padding: 20 }}>
      <Text order={2} align="center" style={{ marginBottom: 20, fontWeight: 600, fontSize: 24 }}>
        Добавление API токена
      </Text>
      <Input
        value={inputValue}
        onChange={handleInputChange}
        placeholder="Укажите API токен здесь..."
        fullWidth
        style={{ marginBottom: 20 }}
      />
      <Button onClick={handleButtonClick} fullWidth>
        Проверить
      </Button>
    </div>
  );
};

export default AddApiToken;
