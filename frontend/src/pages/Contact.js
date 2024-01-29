import React, { useEffect, useState } from 'react';
import { Image, Button } from '@mantine/core';


const Contact = () => {
  const [data, setData] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [isButtonVisible, setButtonVisibility] = useState(true);
  const [hasFetchedData, setHasFetchedData] = useState(false);
  const searchParams = new URLSearchParams(window.location.search);
  const apiToken = searchParams.get('apiToken');

  useEffect(() => {
    const fetchDataWithDelay = async () => {
      try {

        if (apiToken) {
          // const response = await fetch('http://localhost:8000/ads_users/', {
          const response = await fetch('https://retail-extension.bnpi.dev/ads_users', {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Token ${apiToken}`,
            },
          });
  
          if (response.ok) {
            const data = await response.json();
            setData(data);
          } else {
            console.error(`Ошибка запроса: ${response.status}`);
          }
        }
      } catch (error) {
        console.error('Произошла ошибка:', error);
      }
    };
  
    fetchDataWithDelay();
  }, []);

  const handleCheckboxChange = (item) => {
    if (selectedItems.includes(item)) {
      setSelectedItems(selectedItems.filter((selectedItem) => selectedItem !== item));
    } else {
      setSelectedItems([...selectedItems, item]);
    }
  };

  const handleDeleteSelected = () => {
    setData(prevData => prevData.filter((item) => !selectedItems.includes(item)));
    setSelectedItems([]);
  };

  const handleSaveButtonClick = () => {
    const fetchData = async () => {
      try {

        if (apiToken) {
          // const response = await fetch('http://localhost:8000/ads_users/save_all', {
          const response = await fetch('https://retail-extension.bnpi.dev/ads_users/save_all', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Token ${apiToken}`,
            },
            body: JSON.stringify(data.filter((item) => !selectedItems.includes(item))),
          });

          if (response.ok) {
            alert('Данные отправлены, Вы можете закрыть это окно!');
          } else {
            alert(`Ошибка запроса: ${response.status}`);
          }
        }
      } catch (error) {
        console.error('Произошла ошибка:', error);
      }
    };

    fetchData();
  };

  const proccess = () => {
    handleDeleteSelected();
    handleSaveButtonClick();
    setButtonVisibility(false);
  };

  return (
    <div style={{ textAlign: 'center', padding: '20px' }}>
      <h1 style={{ marginBottom: '20px' }}>Собранные объявления</h1>
      <ul style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', padding: 0, listStyle: 'none' }}>
        {data.map((item) => (
          <li key={item.number} style={{ flexBasis: '23%', marginBottom: '20px', borderBottom: '1px solid #ccc', paddingBottom: '20px' }}>
            <label
              htmlFor={`checkbox-${item.number}`}
              style={{
                textAlign: 'center',
                height: '450px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                cursor: 'pointer',
              }}
            >
              <Image src={item.pictures} style={{ maxWidth: 250, height: 250, margin: '0 auto' }} />
              <div>
                <strong>{item.name}</strong>
                <p>Цена: {item.price} руб.</p>
              </div>
              <input
                type="checkbox"
                id={`checkbox-${item.number}`}
                checked={selectedItems.includes(item)}
                onChange={() => handleCheckboxChange(item)}
              />
            </label>
          </li>
        ))}
      </ul>
      <Button 
        style={{ 
          marginTop: '20px',
          display: isButtonVisible ? 'block' : 'none',
          margin: 'auto',
        }} 
        onClick={proccess}
      >
        {selectedItems.length > 0 ? 'Удалить выбранные и продолжить' : 'Продолжить'}
      </Button>
    </div>
  );
  
};

export default Contact;
