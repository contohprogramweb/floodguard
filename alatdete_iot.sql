-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Jun 13, 2026 at 05:41 PM
-- Server version: 8.0.45-cll-lve
-- PHP Version: 8.4.21

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `alatdete_iot`
--

-- --------------------------------------------------------

--
-- Table structure for table `data_sensor`
--

CREATE TABLE `data_sensor` (
  `id_data_sensor` int NOT NULL,
  `id_sensorbox` int DEFAULT NULL,
  `waktu` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `tinggi_air` varchar(50) DEFAULT NULL,
  `suhu` varchar(50) DEFAULT NULL,
  `kelembaban` varchar(50) DEFAULT NULL,
  `curah_hujan` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `data_sensor`
--

INSERT INTO `data_sensor` (`id_data_sensor`, `id_sensorbox`, `waktu`, `tinggi_air`, `suhu`, `kelembaban`, `curah_hujan`) VALUES
(1, 1, '2026-05-10 03:49:38', '120', '28.5', '80', '15');

-- --------------------------------------------------------

--
-- Table structure for table `hasil_klasifikasi`
--

CREATE TABLE `hasil_klasifikasi` (
  `id_hasil_klasifikasi` int NOT NULL,
  `id_data_sensor` int DEFAULT NULL,
  `status_air` varchar(50) DEFAULT NULL,
  `probabilitas` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `hasil_klasifikasi`
--

INSERT INTO `hasil_klasifikasi` (`id_hasil_klasifikasi`, `id_data_sensor`, `status_air`, `probabilitas`) VALUES
(1, 1, 'Waspada', 42);

-- --------------------------------------------------------

--
-- Table structure for table `notifikasi`
--

CREATE TABLE `notifikasi` (
  `id_notifikasi` int NOT NULL,
  `id_hasil_klasifikasi` int DEFAULT NULL,
  `waktu_kirim` datetime DEFAULT NULL,
  `pesan` varchar(500) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `notifikasi`
--

INSERT INTO `notifikasi` (`id_notifikasi`, `id_hasil_klasifikasi`, `waktu_kirim`, `pesan`) VALUES
(1, 1, '2026-05-10 10:49:39', '🌊 *NOTIFIKASI BANJIR*\nHalo Muhammad,\nStatus: *Waspada* (42%)\nTinggi Air : 120 cm\nSuhu       : 28.5 °C\nKelembaban : 80 %\nCurah Hujan: 15 mm\nHarap waspada dan pantau kondisi sekitar.');

-- --------------------------------------------------------

--
-- Table structure for table `sensor_box`
--

CREATE TABLE `sensor_box` (
  `id_sensorbox` int NOT NULL,
  `kode_sensorbox` varchar(5) DEFAULT NULL,
  `nama_pemilik` varchar(100) DEFAULT NULL,
  `alamat_pemilik` varchar(100) DEFAULT NULL,
  `nomor_whatsapp` varchar(20) DEFAULT NULL,
  `password` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `sensor_box`
--

INSERT INTO `sensor_box` (`id_sensorbox`, `kode_sensorbox`, `nama_pemilik`, `alamat_pemilik`, `nomor_whatsapp`, `password`) VALUES
(1, 'E7NX6', 'Muhammad', 'Semarang', '628884018148', '7c4a8d09ca3762af61e59520943dc26494f8941b');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `data_sensor`
--
ALTER TABLE `data_sensor`
  ADD PRIMARY KEY (`id_data_sensor`),
  ADD KEY `fk_ds_sb` (`id_sensorbox`);

--
-- Indexes for table `hasil_klasifikasi`
--
ALTER TABLE `hasil_klasifikasi`
  ADD PRIMARY KEY (`id_hasil_klasifikasi`),
  ADD KEY `fk_hk_ds` (`id_data_sensor`);

--
-- Indexes for table `notifikasi`
--
ALTER TABLE `notifikasi`
  ADD PRIMARY KEY (`id_notifikasi`),
  ADD KEY `fk_notif_hk` (`id_hasil_klasifikasi`);

--
-- Indexes for table `sensor_box`
--
ALTER TABLE `sensor_box`
  ADD PRIMARY KEY (`id_sensorbox`),
  ADD UNIQUE KEY `uq_kode` (`kode_sensorbox`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `data_sensor`
--
ALTER TABLE `data_sensor`
  MODIFY `id_data_sensor` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `hasil_klasifikasi`
--
ALTER TABLE `hasil_klasifikasi`
  MODIFY `id_hasil_klasifikasi` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `notifikasi`
--
ALTER TABLE `notifikasi`
  MODIFY `id_notifikasi` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `sensor_box`
--
ALTER TABLE `sensor_box`
  MODIFY `id_sensorbox` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `data_sensor`
--
ALTER TABLE `data_sensor`
  ADD CONSTRAINT `fk_ds_sb` FOREIGN KEY (`id_sensorbox`) REFERENCES `sensor_box` (`id_sensorbox`) ON DELETE SET NULL;

--
-- Constraints for table `hasil_klasifikasi`
--
ALTER TABLE `hasil_klasifikasi`
  ADD CONSTRAINT `fk_hk_ds` FOREIGN KEY (`id_data_sensor`) REFERENCES `data_sensor` (`id_data_sensor`) ON DELETE SET NULL;

--
-- Constraints for table `notifikasi`
--
ALTER TABLE `notifikasi`
  ADD CONSTRAINT `fk_notif_hk` FOREIGN KEY (`id_hasil_klasifikasi`) REFERENCES `hasil_klasifikasi` (`id_hasil_klasifikasi`) ON DELETE SET NULL;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
