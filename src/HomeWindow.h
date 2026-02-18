#ifndef HOMEWINDOW_H
#define HOMEWINDOW_H

#include <QMainWindow>

class QPushButton;
class QLineEdit;

class HomeWindow : public QMainWindow {
  Q_OBJECT

public:
  explicit HomeWindow(QWidget *parent = nullptr);

private:
  void setupUi();
  void applyStyles();
  void setModeResearcher();
  void setModeAdmin();

  QPushButton *researcherButton_ = nullptr;
  QPushButton *adminButton_ = nullptr;
  QLineEdit *userEdit_ = nullptr;
  QLineEdit *outputDirEdit_ = nullptr;
  QPushButton *beginButton_ = nullptr;
};

#endif
