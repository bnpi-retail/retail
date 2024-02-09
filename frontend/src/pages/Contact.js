import React, { useEffect, useState } from 'react';
import { Image, Button, Blockquote } from '@mantine/core';


const Contact = () => {
  const [data, setData] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [isButtonVisible, setButtonVisibility] = useState(true);
  const [hasFetchedData, setHasFetchedData] = useState(false);
  const [showCheckboxes, setShowCheckboxes] = useState(true);
  const [buttonClicked, setButtonClicked] = useState(false);
  const [saveSuccessful, setSaveSuccessful] = useState(false);

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
            let data
            try {
              data = await response.json();
              setData(data);

            } catch (error) {
              console.log(`Error: ${error}`);
            }
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
            setShowCheckboxes(false);
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
    setButtonClicked(true);
    setSaveSuccessful(true);
  };

  function DemoFirst() {
    return (
      <Blockquote color="rgba(251, 255, 0, 1)" radius="xs" mt="xl">
        Успешно собрано {data.length} товаров, пожалуйста, проверьте и выберите товары, которые необходимо удалить
      </Blockquote>
    );
  }

  function DemoSecond() {
    return (
      <Blockquote color="green" radius="xs" mt="xl">
        Информация о {data.length} товарах сохранена
      </Blockquote>
    );
  }


  return (
    <div style={{ textAlign: 'center', padding: '20px' }}>
      {buttonClicked ? (
        DemoSecond()
      ) : DemoFirst()}
      <ul style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', padding: 0, listStyle: 'none' }}>
      {data.map((item) => (
        <li key={item.number} style={{ flexBasis: '23%', marginBottom: '20px', borderBottom: '1px solid #ccc', paddingBottom: '20px' }}>
          {/* Переход по ссылке при клике на изображение */}
          <div style={{ textAlign: 'center', cursor: 'pointer' }} onClick={() => { 
            window.open(item.href, '_blank'); 
            window.location.href = item.href;
          }}>
            <Image src={item.pictures} style={{ maxWidth: 250, height: 250, margin: '0 auto' }} />
          </div>
          {/* Выбор чекбокса */}
          <div style={{ textAlign: 'center' }}>
            <label
              htmlFor={`checkbox-${item.number}`}
              style={{ display: 'block', marginTop: '10px' }}
            >
              <strong>{item.name}</strong>
              <p>Цена: {item.price} руб.</p>
            </label>
            <input
              type="checkbox"
              id={`checkbox-${item.number}`}
              checked={selectedItems.includes(item)}
              onChange={() => handleCheckboxChange(item)}
              style={{ display: showCheckboxes ? 'block' : 'none' }}
            />
          </div>
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
        {selectedItems.length > 0 
          ? `Удалить ${selectedItems.length} и сохранить ${data.length - selectedItems.length} товаров`
          : `Сохранить ${data.length} товаров`
        }
      </Button>
    </div>
  );
  
};

export default Contact;